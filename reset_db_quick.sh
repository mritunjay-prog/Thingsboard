#!/bin/bash

echo "🔓 Quick Database Service Reset"
echo "==============================="

# Remove lock file (this will force re-initialization)
if [ -f "data/database/.db_service_lock" ]; then
    rm "data/database/.db_service_lock"
    echo "✅ Lock file removed"
    echo "🔄 Database service will re-run on next startup"
else
    echo "ℹ️  Lock file already removed"
fi

echo ""
echo "🎯 Next: Start your API with 'python3 core/api.py'"
echo "✨ Database service will automatically re-initialize!"



