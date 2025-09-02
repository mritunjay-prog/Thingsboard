#!/usr/bin/env python3
"""
Test script for the database service
Run this to test the database service independently
"""

import sys
import os
import time

# Add the core directory to the path
sys.path.insert(0, 'core')

def test_database_service():
    """Test the database service functionality"""
    try:
        print("🧪 Testing Database Service...")
        
        # Import the database service
        from database_service import get_database_service, initialize_database_service
        
        # Get service instance
        service = get_database_service()
        print(f"✅ Service instance created: {type(service).__name__}")
        
        # Check initial status
        print("\n📊 Initial Status:")
        status = service.get_status()
        print(f"   Status: {status}")
        
        # Test initialization
        print("\n🚀 Testing Service Initialization...")
        success = initialize_database_service()
        print(f"   Initialization Result: {success}")
        
        # Check status after initialization
        print("\n📊 Status After Initialization:")
        status = service.get_status()
        print(f"   Status: {status}")
        
        # Test running again (should skip)
        print("\n🔄 Testing Second Run (should skip)...")
        success2 = initialize_database_service()
        print(f"   Second Run Result: {success2}")
        
        # Final status
        print("\n📊 Final Status:")
        final_status = service.get_status()
        print(f"   Status: {final_status}")
        
        print("\n🎉 Database Service Test Completed!")
        
        if final_status.get("status") == "running":
            print(f"🌐 Web Interface: {final_status.get('web_interface')}")
            print(f"📊 Database File: {final_status.get('db_file')}")
            print(f"🐳 Container: {final_status.get('container_name')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test():
    """Cleanup test resources"""
    try:
        print("\n🧹 Cleaning up test resources...")
        
        from database_service import get_database_service
        service = get_database_service()
        
        # Cleanup
        cleanup_success = service.cleanup()
        print(f"   Cleanup Result: {cleanup_success}")
        
        return cleanup_success
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE SERVICE TEST")
    print("=" * 60)
    
    try:
        # Run test
        test_success = test_database_service()
        
        if test_success:
            print("\n✅ Test completed successfully!")
            
            # Ask user if they want to cleanup
            response = input("\n🧹 Do you want to cleanup test resources? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                cleanup_test()
            else:
                print("ℹ️ Test resources left running. Use 'docker ps' to see containers.")
        else:
            print("\n❌ Test failed!")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)



