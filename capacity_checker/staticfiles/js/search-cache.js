/**
 * Client-side caching for search results
 * Reduces server load by caching search results in localStorage
 */
class SearchCache {
    constructor() {
        this.cachePrefix = 'cmr_search_';
        this.maxCacheSize = 5 * 1024 * 1024; // 5MB
        this.defaultTTL = 15 * 60 * 1000; // 15 minutes
        this.cleanupOldEntries();
    }

    /**
     * Generate cache key from search parameters
     */
    getCacheKey(params) {
        const normalized = {
            q: params.query || '',
            p: params.page || 1,
            pp: params.per_page || 25,
            s: params.sort_by || 'relevance',
            o: params.sort_order || 'desc'
        };
        return this.cachePrefix + btoa(JSON.stringify(normalized));
    }

    /**
     * Get cached search results
     */
    get(params) {
        try {
            const key = this.getCacheKey(params);
            const cached = localStorage.getItem(key);
            
            if (!cached) return null;
            
            const data = JSON.parse(cached);
            
            // Check if expired
            if (Date.now() > data.expires) {
                localStorage.removeItem(key);
                return null;
            }
            
            console.log('✅ Cache hit for search:', params.query);
            return data.results;
        } catch (e) {
            console.error('Cache read error:', e);
            return null;
        }
    }

    /**
     * Store search results in cache
     */
    set(params, results, ttl = this.defaultTTL) {
        try {
            const key = this.getCacheKey(params);
            const data = {
                results: results,
                expires: Date.now() + ttl,
                query: params.query,
                timestamp: Date.now()
            };
            
            const serialized = JSON.stringify(data);
            
            // Check size before storing
            if (serialized.length > this.maxCacheSize / 10) {
                console.warn('Search result too large to cache');
                return false;
            }
            
            // Try to store, handle quota exceeded
            try {
                localStorage.setItem(key, serialized);
                console.log('✅ Cached search results for:', params.query);
                return true;
            } catch (e) {
                if (e.name === 'QuotaExceededError') {
                    this.makeSpace(serialized.length);
                    localStorage.setItem(key, serialized);
                    return true;
                }
                throw e;
            }
        } catch (e) {
            console.error('Cache write error:', e);
            return false;
        }
    }

    /**
     * Clear expired entries
     */
    cleanupOldEntries() {
        try {
            const now = Date.now();
            const keys = Object.keys(localStorage);
            let cleaned = 0;
            
            keys.forEach(key => {
                if (key.startsWith(this.cachePrefix)) {
                    try {
                        const data = JSON.parse(localStorage.getItem(key));
                        if (data.expires < now) {
                            localStorage.removeItem(key);
                            cleaned++;
                        }
                    } catch (e) {
                        // Invalid entry, remove it
                        localStorage.removeItem(key);
                        cleaned++;
                    }
                }
            });
            
            if (cleaned > 0) {
                console.log(`🧹 Cleaned ${cleaned} expired cache entries`);
            }
        } catch (e) {
            console.error('Cache cleanup error:', e);
        }
    }

    /**
     * Make space by removing oldest entries
     */
    makeSpace(bytesNeeded) {
        const entries = [];
        const keys = Object.keys(localStorage);
        
        // Collect all cache entries
        keys.forEach(key => {
            if (key.startsWith(this.cachePrefix)) {
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    entries.push({
                        key: key,
                        timestamp: data.timestamp || 0,
                        size: localStorage.getItem(key).length
                    });
                } catch (e) {
                    // Invalid entry
                    localStorage.removeItem(key);
                }
            }
        });
        
        // Sort by timestamp (oldest first)
        entries.sort((a, b) => a.timestamp - b.timestamp);
        
        // Remove oldest entries until we have enough space
        let removed = 0;
        for (const entry of entries) {
            localStorage.removeItem(entry.key);
            removed += entry.size;
            if (removed >= bytesNeeded) break;
        }
    }

    /**
     * Clear all search cache
     */
    clear() {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith(this.cachePrefix)) {
                localStorage.removeItem(key);
            }
        });
        console.log('🗑️ Search cache cleared');
    }
}

// Initialize cache and make it globally available
window.searchCache = new SearchCache();

// Hook into search form if it exists
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.querySelector('form[action="/search/"]');
    if (!searchForm) return;
    
    searchForm.addEventListener('submit', function(e) {
        // Get search parameters
        const formData = new FormData(searchForm);
        const params = {
            query: formData.get('q') || '',
            page: 1,
            per_page: formData.get('per_page') || 25,
            sort_by: formData.get('sort_by') || 'relevance',
            sort_order: formData.get('sort_order') || 'desc'
        };
        
        // Check cache first
        const cached = window.searchCache.get(params);
        if (cached) {
            // We have cached results, but form submission will still happen
            // This is just to prepare the cache
            console.log('Search will use cached results if available');
        }
    });
});