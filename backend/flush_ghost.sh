#!/bin/bash
# 👻 Vibehack Redis Ghost Flush Script

echo "🧹 Evicting orphan ghost signatures from Redis..."
if command -v redis-cli &> /dev/null; then
    # Ping Redis to make sure it's active
    if [ "$(redis-cli ping)" = "PONG" ]; then
        # Find all room keys
        ROOM_KEYS=$(redis-cli keys "room_users:*")
        GHOST_KEYS=$(redis-cli keys "ghost_pointer:*")
        SID_KEYS=$(redis-cli keys "ghost_to_sid:*")

        if [ -n "$ROOM_KEYS" ]; then
            echo "Deleting room user sets..."
            echo "$ROOM_KEYS" | xargs redis-cli del
        fi

        if [ -n "$GHOST_KEYS" ]; then
            echo "Deleting ghost identity pointers..."
            echo "$GHOST_KEYS" | xargs redis-cli del
        fi

        if [ -n "$SID_KEYS" ]; then
            echo "Deleting socket SID pointers..."
            echo "$SID_KEYS" | xargs redis-cli del
        fi

        echo "✅ All loop residuals successfully purged. Dashboard counts reset to 0!"
    else
        echo "❌ Redis is not responding to ping."
    fi
else
    echo "❌ redis-cli tool not found."
fi

