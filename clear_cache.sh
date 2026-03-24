#!/bin/bash

echo "🧹 تنظيف الملفات المخزنة مؤقتاً..."
echo ""

# حذف مجلدات __pycache__
find . -type d -name "__pycache__" -print -exec rm -rf {} + 2>/dev/null

# حذف ملفات .pyc
find . -name "*.pyc" -print -delete 2>/dev/null

echo ""
echo "✅ تم التنظيف بنجاح!"
echo ""
echo "الآن قم بإعادة تشغيل السيرفر:"
echo "  python manage.py runserver"
