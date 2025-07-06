#!/usr/bin/env python3
"""
Install monitoring dependencies for enhanced debugging
"""
import subprocess
import sys

def install_psutil():
    """Install psutil for memory monitoring"""
    try:
        import psutil
        print("✅ psutil is already installed")
        return True
    except ImportError:
        print("📦 Installing psutil for memory monitoring...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
            print("✅ psutil installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install psutil: {e}")
            return False

if __name__ == "__main__":
    print("🔧 Setting up monitoring dependencies...")
    
    success = install_psutil()
    
    if success:
        print("✅ All monitoring dependencies are ready!")
        print("🚀 Enhanced monitoring will now track:")
        print("   - Memory usage per API call")
        print("   - Egress bandwidth")
        print("   - Performance metrics")
        print("   - Real-time alerts for issues")
    else:
        print("⚠️  Some dependencies failed to install")
        print("💡 Memory monitoring will be disabled but other monitoring will work")