"""HotelOS cash-collection report (INR; all amounts are integer paise).

Requires the previously supplied services.py for authentication and JSON reading.
Register in main.py BEFORE catch-all routes:
    from revenue import router as revenue_router
    app.include_router(revenue_router)

Each reservation needs these NEW fields, maintained by booking/payment code:
    room_total_paise: agreed total room charge, fixed at booking
    room_paid_paise: actual cumulative room payments received, net of refunds
    service_paid_paise: actual cumulative service payments received, net of refunds
Do not infer payments from checked_in/checked_out status. Missing fields are
reported as incomplete, never silently counted as zero. Explicit zero is valid.
This module only reads data; it does not collect or record payments.
"""
from fastapi import APIRouter, Depends, HTTPException
from services import authenticate, read_records, same_id, store_lock

router = APIRouter(prefix='/api/revenue', tags=['Revenue'])


def admin_only(actor=Depends(authenticate)):
    if actor['role'] != 'Admin':
        raise HTTPException(403, 'Only Admin can view hotel revenue')
    return actor


def money(record, field):
    value = record.get(field)
    if type(value) is not int or value < 0:
        raise ValueError(f'{field} must be a nonnegative integer in paise')
    return value


def calculate_revenue(reservations, services):
    """Pure function: report recorded collections, bills and payment targets.

    No status-based assumption that money was received. Completed services are
    charges; pending/in-progress services are only estimates. Cancelled services
    have no charge. Room total includes the full agreed stay, not nightly rate.
    """
    details, incomplete, invalid_services = [], [], []
    room_collected = service_collected = room_billed = service_billed = 0
    outstanding = credit = 0
    ids = [str(r.get('reservation_id', r.get('id'))) for r in reservations]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate reservation IDs; fix data before reporting')
    for reservation in reservations:
        rid = reservation.get('reservation_id', reservation.get('id'))
        errors = []
        values = {}
        for field in ('room_total_paise', 'room_paid_paise', 'service_paid_paise'):
            try:
                values[field] = money(reservation, field)
            except ValueError as exc:
                errors.append(str(exc))
        if rid is None:
            errors.append('Missing reservation ID')
        if errors:
            incomplete.append({'reservation_id': rid, 'problems': errors})
            continue
        completed, pending = 0, 0
        for item in services:
            if not same_id(item.get('reservation_id'), rid):
                continue
            try:
                amount = money(item, 'amount_paise')
                status = item.get('status')
                if status == 'completed':
                    completed += amount
                elif status in ('pending', 'in_progress'):
                    pending += amount
                elif status != 'cancelled':
                    raise ValueError('Unknown service status')
            except ValueError as exc:
                errors.append(f'Service {item.get("service_id")}: {exc}')
        if errors:
            incomplete.append({'reservation_id': rid, 'problems': errors})
            continue
        total = values['room_total_paise']
        paid_room = values['room_paid_paise']
        paid_services = values['service_paid_paise']
        # Round the 30% deposit to nearest paise (half up); remainder is exact.
        deposit = (total * 30 + 50) // 100
        balance = total + completed - paid_room - paid_services
        details.append({
            'reservation_id': str(rid), 'room_total_paise': total,
            'checkin_30_percent_paise': deposit,
            'checkout_70_percent_paise': total - deposit,
            'room_collected_paise': paid_room,
            'service_collected_paise': paid_services,
            'completed_service_charges_paise': completed,
            'pending_service_estimate_paise': pending,
            'remaining_balance_paise': max(0, balance),
            'credit_paise': max(0, -balance),
        })
        room_collected += paid_room
        service_collected += paid_services
        room_billed += total
        service_billed += completed
        outstanding += max(0, balance)
        credit += max(0, -balance)
    for item in services:
        if item.get('reservation_id') is None or str(item['reservation_id']) not in ids:
            invalid_services.append(item.get('service_id'))
    return {
        'currency': 'INR',
        'report_complete': not incomplete and not invalid_services,
        'room_collected_paise': room_collected,
        'service_collected_paise': service_collected,
        'total_collected_paise': room_collected + service_collected,
        'room_charges_paise': room_billed,
        'completed_service_charges_paise': service_billed,
        'outstanding_balance_paise': outstanding,
        'credit_paise': credit,
        'included_reservations': details,
        'excluded_reservations': incomplete,
        'orphan_service_ids': invalid_services,
        'note': 'Totals cover included reservations only. Collections are recorded cash, '
                'not profit or accounting revenue. No date filtering or payment history.',
    }


@router.get('/summary')
def revenue_summary(actor=Depends(admin_only)):
    with store_lock:
        reservations = read_records('reservations.json')
        services = read_records('services.json', allow_missing=True)
    try:
        return calculate_revenue(reservations, services)
    except ValueError as exc:
        raise HTTPException(503, str(exc))
