#!/usr/bin/env python3
"""
Test script for lottery checker
Run this to test the functionality locally
"""

import os
import sys
from datetime import datetime


def test_environment():
    """Test if environment variables are set"""
    print("🔍 Testing environment variables...")

    numero = os.getenv("LOTTERY_NUMBER")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not numero:
        print("❌ LOTTERY_NUMBER not set")
        print("   Set it with: export LOTTERY_NUMBER='your_lottery_number'")
        return False
    else:
        print(f"✅ LOTTERY_NUMBER: {numero}")

    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set")
        print("   Set it with: export DISCORD_WEBHOOK_URL='your_webhook_url'")
        return False
    else:
        print(f"✅ DISCORD_WEBHOOK_URL: {webhook_url[:50]}...")

    return True


def test_dependencies():
    """Test if required packages are installed"""
    print("\n📦 Testing dependencies...")

    required_packages = ["requests", "bs4", "lxml"]

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is not installed")
            print(f"   Install with: pip install {package}")
            return False

    return True


def test_date_calculation():
    """Test the Saturday date calculation"""
    print("\n📅 Testing date calculation...")

    try:
        from lottery_checker import get_saturday_date

        saturday_date = get_saturday_date()
        print(f"✅ Saturday date: {saturday_date}")
        return True
    except Exception as e:
        print(f"❌ Error calculating Saturday date: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Running lottery checker tests...\n")

    tests = [
        ("Environment Variables", test_environment),
        ("Dependencies", test_dependencies),
        ("Date Calculation", test_date_calculation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Testing: {test_name}")
        if test_func():
            passed += 1
        print()

    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! You can now run the lottery checker.")
        print("   Run: python lottery_checker.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
