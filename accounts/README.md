# Accounts Module - Simplified Driver Session Tracking

## 📋 ملخص التغييرات

### قبل (3 موديلات):
```
DriverWorkLog      ──► سجل online/offline events
DriverDailyStats   ──► إحصائيات يومية محسوبة  
DriverSession      ──► جلسات عمل (تكرار!)
```

### بعد (موديل واحد):
```
DriverSession      ──► يحتوي كل شيء!
```

---

## ✅ المميزات

| الجانب | قبل | بعد |
|--------|-----|-----|
| عدد الموديلات | 3 | 1 |
| التعقيد | عالي | بسيط |
| الـ Queries | متعددة | مباشرة |
| الصيانة | صعبة | سهلة |
| الأداء | يحتاج حساب | On-demand |

---

## 🔗 الـ Endpoints (بدون تغيير!)

جميع الـ endpoints تعمل بنفس الطريقة:

```
POST   /accounts/driver/go-online/      ← تسجيل دخول السائق
POST   /accounts/driver/go-offline/     ← تسجيل خروج السائق
GET    /accounts/driver/status/         ← حالة السائق

GET    /accounts/driver/stats/today/    ← إحصائيات اليوم
GET    /accounts/driver/stats/daily/    ← إحصائيات يوم محدد
GET    /accounts/driver/stats/weekly/   ← إحصائيات الأسبوع
GET    /accounts/driver/stats/monthly/  ← إحصائيات الشهر
GET    /accounts/driver/stats/range/    ← إحصائيات فترة
GET    /accounts/driver/logs/           ← سجلات العمل
```

---

## 🔄 كيف يعمل DriverSession

```
┌─────────────────────────────────────────────────────────┐
│                    go_online()                          │
│                         │                               │
│                         ▼                               │
│   ┌─────────────────────────────────────────────────┐  │
│   │  DriverSession.start_session(driver)            │  │
│   │  ├── إنهاء أي جلسة نشطة سابقة                   │  │
│   │  └── إنشاء جلسة جديدة (is_active=True)         │  │
│   └─────────────────────────────────────────────────┘  │
│                                                         │
│                    go_offline()                         │
│                         │                               │
│                         ▼                               │
│   ┌─────────────────────────────────────────────────┐  │
│   │  DriverSession.end_active_session(driver)       │  │
│   │  ├── البحث عن الجلسة النشطة                     │  │
│   │  ├── تحديث ended_at = now()                     │  │
│   │  ├── حساب duration_seconds                      │  │
│   │  └── تحديث is_active = False                    │  │
│   └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 حساب الإحصائيات

```python
# إحصائيات اليوم
stats = DriverSession.get_today_stats(driver)

# إحصائيات يوم محدد
stats = DriverSession.get_daily_stats(driver, date)

# إحصائيات فترة
stats = DriverSession.get_range_stats(driver, start_date, end_date)

# إحصائيات الأسبوع
stats = DriverSession.get_week_stats(driver)

# إحصائيات الشهر
stats = DriverSession.get_month_stats(driver, month, year)
```

### Response Format:
```json
{
    "date": "2024-01-15",
    "total_online_seconds": 28800,
    "total_hours": 8.0,
    "formatted_hours": "08:00:00",
    "total_sessions": 2,
    "first_online": "2024-01-15T08:00:00Z",
    "last_offline": "2024-01-15T17:00:00Z"
}
```

---

## 🔧 Migration Guide

### 1. Backup البيانات القديمة (اختياري)
```sql
-- حفظ البيانات قبل الحذف
CREATE TABLE driver_work_log_backup AS SELECT * FROM accounts_driverworklog;
CREATE TABLE driver_daily_stats_backup AS SELECT * FROM accounts_driverdailystats;
```

### 2. تحويل البيانات (اختياري)
```python
# إذا أردت تحويل البيانات القديمة إلى DriverSession
from accounts.models import DriverWorkLog, DriverSession
from django.utils import timezone

def migrate_old_data():
    """تحويل DriverWorkLog القديم إلى DriverSession"""
    drivers = User.objects.filter(role='driver')
    
    for driver in drivers:
        logs = DriverWorkLog.objects.filter(driver=driver).order_by('timestamp')
        
        online_time = None
        for log in logs:
            if log.status == 'online':
                online_time = log.timestamp
            elif log.status == 'offline' and online_time:
                # إنشاء session
                duration = (log.timestamp - online_time).total_seconds()
                DriverSession.objects.create(
                    driver=driver,
                    date=online_time.date(),
                    started_at=online_time,
                    ended_at=log.timestamp,
                    duration_seconds=int(duration),
                    is_active=False
                )
                online_time = None
```

### 3. حذف الموديلات القديمة
```python
# بعد التأكد من عمل النظام الجديد
# احذف من models.py:
# - class DriverWorkLog
# - class DriverDailyStats
```

### 4. تشغيل migrations
```bash
python manage.py makemigrations accounts
python manage.py migrate
```

---

## 📁 الملفات المعدلة

| الملف | التغيير |
|-------|---------|
| `models.py` | موديل واحد `DriverSession` مع كل الـ methods |
| `views.py` | يستخدم `DriverSession` بدلاً من الموديلات القديمة |
| `serializers.py` | تنظيف بسيط |
| `urls.py` | بدون تغيير ✅ |
| `admin.py` | واجهة محسنة لـ `DriverSession` |

---

## ⚠️ ملاحظات مهمة

1. **الـ Response format لم يتغير** - التطبيق سيعمل بدون تعديل على الـ frontend

2. **الجلسات النشطة** تُحسب ديناميكياً (من started_at حتى الآن)

3. **إنهاء الجلسات القديمة** يحدث تلقائياً عند بدء جلسة جديدة

4. **الـ Logs endpoint** يُولّد من sessions (online/offline events)

---

## 🧪 اختبار النظام

```python
from accounts.models import User, DriverSession
from django.utils import timezone

# الحصول على سائق
driver = User.objects.filter(role='driver').first()

# تسجيل دخول
driver.go_online()
print(driver.is_online)  # True

# التحقق من الجلسة
session = DriverSession.objects.filter(driver=driver, is_active=True).first()
print(session.duration_display)  # 00:00:15 (مثلاً)

# إحصائيات اليوم
stats = DriverSession.get_today_stats(driver)
print(stats)

# تسجيل خروج
driver.go_offline()
print(driver.is_online)  # False
```
