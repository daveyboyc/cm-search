/**
 * Client-side cache manager using localStorage
 */
class CacheManager {
    constructor(prefix = 'cmr_cache_') {
        this.prefix = prefix;
        this.maxAge = 30 * 60 * 1000; // 30 minutes default
        this.maxSize = 5 * 1024 * 1024; // 5MB max localStorage
    }

    /**
     * Get item from cache
     */
    get(key) {
        try {
            const item = localStorage.getItem(this.prefix + key);
            if (!item) return null;
            
            const data = JSON.parse(item);
            
            // Check if expired
            if (Date.now() > data.expires) {
                this.remove(key);
                return null;
            }
            
            return data.value;
        } catch (e) {
            console.error('Cache get error:', e);
            return null;
        }
    }

    /**
     * Set item in cache
     */
    set(key, value, maxAge = this.maxAge) {
        try {
            const data = {
                value: value,
                expires: Date.now() + maxAge
            };
            
            const serialized = JSON.stringify(data);
            
            // Check size before storing
            if (serialized.length > this.maxSize / 10) {
                console.warn('Item too large for cache:', key);
                return false;
            }
            
            // Try to store, handle quota exceeded
            try {
                localStorage.setItem(this.prefix + key, serialized);
                return true;
            } catch (e) {
                if (e.name === 'QuotaExceededError') {
                    // Clear old items and try again
                    this.clearOldest();
                    localStorage.setItem(this.prefix + key, serialized);
                    return true;
                }
                throw e;
            }
        } catch (e) {
            console.error('Cache set error:', e);
            return false;
        }
    }

    /**
     * Remove item from cache
     */
    remove(key) {
        localStorage.removeItem(this.prefix + key);
    }

    /**
     * Clear oldest items when quota exceeded
     */
    clearOldest() {
        const items = [];
        
        // Collect all cache items
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                try {
                    const item = JSON.parse(localStorage.getItem(key));
                    items.push({ key, expires: item.expires });
                } catch (e) {
                    // Invalid item, remove it
                    localStorage.removeItem(key);
                }
            }
        }
        
        // Sort by expiration time (oldest first)
        items.sort((a, b) => a.expires - b.expires);
        
        // Remove oldest 25%
        const removeCount = Math.ceil(items.length / 4);
        for (let i = 0; i < removeCount; i++) {
            localStorage.removeItem(items[i].key);
        }
    }

    /**
     * Clear all cache
     */
    clear() {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                keys.push(key);
            }
        }
        keys.forEach(key => localStorage.removeItem(key));
    }

    /**
     * Get cache stats
     */
    getStats() {
        let count = 0;
        let size = 0;
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.prefix)) {
                count++;
                const item = localStorage.getItem(key);
                if (item) size += item.length;
            }
        }
        
        return {
            count: count,
            size: size,
            sizeKB: (size / 1024).toFixed(2),
            sizeMB: (size / 1024 / 1024).toFixed(2)
        };
    }
}

// Create global instance
window.cacheManager = new CacheManager();