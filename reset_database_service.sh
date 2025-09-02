#!/bin/bash

echo "🗑️  Database Service Reset Script"
echo "=================================="

# Check if running as root (for Docker commands)
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Running as root - this is not recommended"
fi

echo ""
echo "🔍 Current Status:"
echo "=================="

# Check if lock file exists
if [ -f "data/database/.db_service_lock" ]; then
    echo "✅ Lock file exists"
    echo "   Location: data/database/.db_service_lock"
else
    echo "❌ Lock file not found"
fi

# Check if database file exists
if [ -f "data/database/papaya-parking-data.db" ]; then
    echo "✅ Database file exists"
    echo "   Size: $(du -h data/database/papaya-parking-data.db | cut -f1)"
else
    echo "❌ Database file not found"
fi

# Check if Docker container is running
if docker ps | grep -q "sqlite-papaya-parking-data"; then
    echo "✅ Docker container is running"
    echo "   Container: $(docker ps --filter name=sqlite-papaya-parking-data --format '{{.Names}}')"
else
    echo "❌ Docker container not running"
fi

echo ""
echo "🗑️  Reset Options:"
echo "=================="
echo "1) Remove lock file only (will re-run service)"
echo "2) Remove lock file + database (fresh start)"
echo "3) Remove lock file + database + container (complete reset)"
echo "4) Exit without changes"

read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🔓 Removing lock file only..."
        if [ -f "data/database/.db_service_lock" ]; then
            rm "data/database/.db_service_lock"
            echo "✅ Lock file removed"
        else
            echo "ℹ️  Lock file already removed"
        fi
        echo "🔄 Service will re-run on next startup"
        ;;
    2)
        echo ""
        echo "🔓 Removing lock file and database..."
        if [ -f "data/database/.db_service_lock" ]; then
            rm "data/database/.db_service_lock"
            echo "✅ Lock file removed"
        fi
        if [ -f "data/database/papaya-parking-data.db" ]; then
            rm "data/database/papaya-parking-data.db"
            echo "✅ Database file removed"
        fi
        echo "🔄 Service will re-run and create fresh database on next startup"
        ;;
    3)
        echo ""
        echo "🔓 Complete reset - removing everything..."
        
        # Remove lock file
        if [ -f "data/database/.db_service_lock" ]; then
            rm "data/database/.db_service_lock"
            echo "✅ Lock file removed"
        fi
        
        # Remove database file
        if [ -f "data/database/papaya-parking-data.db" ]; then
            rm "data/database/papaya-parking-data.db"
            echo "✅ Database file removed"
        fi
        
        # Stop and remove Docker container
        if docker ps | grep -q "sqlite-papaya-parking-data"; then
            echo "🐳 Stopping Docker container..."
            docker stop sqlite-papaya-parking-data
            echo "✅ Container stopped"
            
            echo "🐳 Removing Docker container..."
            docker rm sqlite-papaya-parking-data
            echo "✅ Container removed"
        else
            echo "ℹ️  Docker container not running"
        fi
        
        echo "🔄 Complete reset done - service will re-deploy everything on next startup"
        ;;
    4)
        echo ""
        echo "ℹ️  No changes made"
        ;;
    *)
        echo ""
        echo "❌ Invalid option"
        ;;
esac

echo ""
echo "📊 Final Status:"
echo "================"

# Check final status
if [ -f "data/database/.db_service_lock" ]; then
    echo "✅ Lock file: EXISTS"
else
    echo "❌ Lock file: REMOVED"
fi

if [ -f "data/database/papaya-parking-data.db" ]; then
    echo "✅ Database file: EXISTS"
else
    echo "❌ Database file: REMOVED"
fi

if docker ps | grep -q "sqlite-papaya-parking-data"; then
    echo "✅ Docker container: RUNNING"
else
    echo "❌ Docker container: STOPPED/REMOVED"
fi

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo "1) Start your API: python3 core/api.py"
echo "2) Database service will automatically re-initialize"
echo "3) Check status with RPC: database.status"
echo "4) Access web interface at the URL shown in console"

echo ""
echo "✨ Reset script completed!"



