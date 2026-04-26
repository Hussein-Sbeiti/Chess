#!/usr/bin/env python3
"""Quick test to verify the timer implementation works."""

from game.game_models import GameTimer

def test_timer_basic():
    """Test basic timer functionality."""
    timer = GameTimer()
    
    # Test initial state
    assert timer.white_remaining == 300, "White should start with 300 seconds"
    assert timer.black_remaining == 300, "Black should start with 300 seconds"
    assert timer.is_active is True, "Timer should be active by default"
    
    # Test formatting
    assert timer.format_time(300) == "5:00", "300 seconds should format as 5:00"
    assert timer.format_time(65) == "1:05", "65 seconds should format as 1:05"
    assert timer.format_time(3665) == "1:01:05", "3665 seconds should format as 1:01:05"
    
    # Test decrement
    timer.decrement_active_player("white")
    assert timer.white_remaining == 299, "White time should decrement by 1"
    assert timer.black_remaining == 300, "Black time should remain unchanged"
    
    timer.decrement_active_player("black")
    assert timer.white_remaining == 299, "White time should remain at 299"
    assert timer.black_remaining == 299, "Black time should decrement to 299"
    
    # Test pause/resume
    timer.pause()
    assert timer.is_active is False, "Timer should be paused"
    timer.decrement_active_player("white")
    assert timer.white_remaining == 299, "Paused timer should not decrement"
    
    timer.resume()
    assert timer.is_active is True, "Timer should be resumed"
    timer.decrement_active_player("white")
    assert timer.white_remaining == 298, "Active timer should decrement"
    
    # Test expiration detection
    timer.white_remaining = 0
    assert timer.has_time_expired() is True, "Timer should detect expiration"
    assert timer.get_expired_player() == "white", "Should identify white as expired"
    
    # Test reset
    timer.reset(600)
    assert timer.white_remaining == 600, "White should reset to 600 seconds"
    assert timer.black_remaining == 600, "Black should reset to 600 seconds"
    assert timer.is_active is True, "Timer should be active after reset"
    
    print("✓ All timer tests passed!")

if __name__ == "__main__":
    test_timer_basic()
