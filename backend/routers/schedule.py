from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import get_db
from routers.auth import get_current_admin

router = APIRouter()


class ScheduleCreate(BaseModel):
    staff_id: int
    day_of_week: int  # 0=Monday ... 6=Sunday
    start_time: str   # HH:MM
    end_time: str     # HH:MM
    is_active: int = 1


@router.get("/schedules")
async def get_schedules(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, st.name as staff_name, st.avatar_color
        FROM schedules s
        LEFT JOIN staff st ON s.staff_id = st.id
        WHERE s.admin_id = ?
        ORDER BY s.staff_id, s.day_of_week
    """, (admin["admin_id"],))
    schedules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return schedules


@router.post("/schedules")
async def create_schedule(schedule: ScheduleCreate, admin: dict = Depends(get_current_admin)):
    if schedule.day_of_week < 0 or schedule.day_of_week > 6:
        raise HTTPException(status_code=400, detail="day_of_week must be 0-6 (Mon-Sun)")

    conn = get_db()
    cursor = conn.cursor()

    # Verify staff belongs to this admin
    cursor.execute("SELECT * FROM staff WHERE id = ? AND admin_id = ?", (schedule.staff_id, admin["admin_id"]))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise HTTPException(status_code=404, detail="员工不存在")

    # Upsert: if schedule for this staff+day exists, update it
    cursor.execute(
        "SELECT * FROM schedules WHERE staff_id = ? AND day_of_week = ? AND admin_id = ?",
        (schedule.staff_id, schedule.day_of_week, admin["admin_id"])
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE schedules SET start_time = ?, end_time = ?, is_active = ? WHERE id = ?",
            (schedule.start_time, schedule.end_time, schedule.is_active, existing["id"])
        )
        schedule_id = existing["id"]
    else:
        cursor.execute(
            "INSERT INTO schedules (admin_id, staff_id, day_of_week, start_time, end_time, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            (admin["admin_id"], schedule.staff_id, schedule.day_of_week, schedule.start_time, schedule.end_time, schedule.is_active)
        )
        schedule_id = cursor.lastrowid

    conn.commit()
    cursor.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    result = dict(cursor.fetchone())
    conn.close()
    return result


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedules WHERE id = ? AND admin_id = ?", (schedule_id, admin["admin_id"]))
    schedule = cursor.fetchone()
    if not schedule:
        conn.close()
        raise HTTPException(status_code=404, detail="排班规则不存在")

    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return {"message": "排班规则已删除"}
