/**
 * Time formatting utilities for client-side display
 * Provides consistent 12-hour (AM/PM) time formatting across the application
 */

(function() {
    'use strict';

    // Feature flag: set to false to disable 12-hour format (fallback to ISO)
    const USE_12H_FORMAT = (typeof window !== 'undefined' && window.USE_12H_FORMAT !== undefined) 
        ? window.USE_12H_FORMAT 
        : true;  // Default to true

    /**
     * Format an ISO timestamp or Date object to 12-hour time string (e.g., "2:05 PM")
     * @param {string|Date|number} ts - ISO timestamp string, Date object, or milliseconds timestamp
     * @returns {string} Formatted time string in 12-hour format, or raw ISO if invalid
     */
    function formatTime12h(ts) {
        if (!USE_12H_FORMAT) {
            // Fallback: return ISO string if feature is disabled
            if (typeof ts === 'string') return ts;
            if (ts instanceof Date) return ts.toISOString();
            return String(ts);
        }

        try {
            let date;
            
            // Handle different input types
            if (ts instanceof Date) {
                date = ts;
            } else if (typeof ts === 'string') {
                // Parse ISO string
                date = new Date(ts);
            } else if (typeof ts === 'number') {
                // Assume milliseconds timestamp
                date = new Date(ts);
            } else {
                throw new Error('Invalid timestamp type');
            }

            // Check if date is valid
            if (isNaN(date.getTime())) {
                throw new Error('Invalid date');
            }

            // Format to 12-hour time with locale support
            return date.toLocaleTimeString([], { 
                hour: 'numeric', 
                minute: '2-digit', 
                hour12: true 
            });
        } catch (error) {
            // Graceful fallback: return raw ISO string
            console.warn('[TIME-UTILS] Failed to format time:', ts, error);
            const fallback = typeof ts === 'string' ? ts : (ts instanceof Date ? ts.toISOString() : String(ts));
            return fallback;
        }
    }

    /**
     * Format time with tooltip showing raw ISO for debugging
     * @param {string|Date|number} ts - ISO timestamp string, Date object, or milliseconds timestamp
     * @returns {Object} Object with formatted string and tooltip text
     */
    function formatTime12hWithTooltip(ts) {
        const formatted = formatTime12h(ts);
        let tooltip = '';
        
        try {
            let date;
            if (ts instanceof Date) {
                date = ts;
            } else if (typeof ts === 'string') {
                date = new Date(ts);
            } else if (typeof ts === 'number') {
                date = new Date(ts);
            }
            
            if (date && !isNaN(date.getTime())) {
                tooltip = date.toISOString();
            } else {
                tooltip = 'Time unavailable';
            }
        } catch (error) {
            tooltip = 'Time unavailable';
        }
        
        return {
            formatted: formatted,
            tooltip: tooltip
        };
    }

    // Export to window for global access
    if (typeof window !== 'undefined') {
        window.TimeUtils = {
            formatTime12h: formatTime12h,
            formatTime12hWithTooltip: formatTime12hWithTooltip,
            USE_12H_FORMAT: USE_12H_FORMAT
        };
    }

    // Also support CommonJS/Node.js if needed
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            formatTime12h: formatTime12h,
            formatTime12hWithTooltip: formatTime12hWithTooltip,
            USE_12H_FORMAT: USE_12H_FORMAT
        };
    }

})();

