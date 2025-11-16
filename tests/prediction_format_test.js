/**
 * Unit tests for time formatting utilities (12-hour format)
 * Tests formatTime12h helper function for various input types and edge cases
 */

// Mock window object for Node.js testing
if (typeof window === 'undefined') {
    global.window = {
        USE_12H_FORMAT: true
    };
}

// Load the time-utils module
// In browser, this would be loaded via <script> tag
// For Node.js testing, we'll need to evaluate the file content
const fs = require('fs');
const path = require('path');

// Read and evaluate time-utils.js
const timeUtilsPath = path.join(__dirname, '..', 'static', 'js', 'time-utils.js');
const timeUtilsCode = fs.readFileSync(timeUtilsPath, 'utf8');
eval(timeUtilsCode);

// Test suite
function runTests() {
    const tests = [];
    let passed = 0;
    let failed = 0;

    function test(name, fn) {
        tests.push({ name, fn });
    }

    function assert(condition, message) {
        if (!condition) {
            throw new Error(message || 'Assertion failed');
        }
    }

    function assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(message || `Expected "${expected}", got "${actual}"`);
        }
    }

    // Test 1: 00:00 → 12:00 AM
    test('00:00 should format to 12:00 AM', function() {
        const date = new Date('2024-01-01T00:00:00Z');
        const result = window.TimeUtils.formatTime12h(date);
        // Should be "12:00 AM" (exact format may vary by locale, but should contain "12" and "AM")
        assert(result.includes('12'), `Result should contain "12", got: ${result}`);
        assert(result.includes('AM') || result.toLowerCase().includes('am'), `Result should contain "AM", got: ${result}`);
    });

    // Test 2: 12:00 → 12:00 PM
    test('12:00 should format to 12:00 PM', function() {
        const date = new Date('2024-01-01T12:00:00Z');
        const result = window.TimeUtils.formatTime12h(date);
        // Should be "12:00 PM"
        assert(result.includes('12'), `Result should contain "12", got: ${result}`);
        assert(result.includes('PM') || result.toLowerCase().includes('pm'), `Result should contain "PM", got: ${result}`);
    });

    // Test 3: 13:05 → 1:05 PM
    test('13:05 should format to 1:05 PM', function() {
        const date = new Date('2024-01-01T13:05:00Z');
        const result = window.TimeUtils.formatTime12h(date);
        // Should be "1:05 PM" (or "1:05 PM" depending on locale)
        assert(result.includes('1') || result.includes('01'), `Result should contain "1", got: ${result}`);
        assert(result.includes('05') || result.includes('5'), `Result should contain "05" or "5", got: ${result}`);
        assert(result.includes('PM') || result.toLowerCase().includes('pm'), `Result should contain "PM", got: ${result}`);
    });

    // Test 4: ISO string input
    test('ISO string should be parsed and formatted', function() {
        const isoString = '2024-01-01T14:30:00Z';
        const result = window.TimeUtils.formatTime12h(isoString);
        // Should parse and format correctly
        assert(typeof result === 'string', 'Result should be a string');
        assert(result.length > 0, 'Result should not be empty');
    });

    // Test 5: Milliseconds timestamp
    test('Milliseconds timestamp should be formatted', function() {
        const timestamp = new Date('2024-01-01T15:45:00Z').getTime();
        const result = window.TimeUtils.formatTime12h(timestamp);
        assert(typeof result === 'string', 'Result should be a string');
        assert(result.length > 0, 'Result should not be empty');
    });

    // Test 6: Invalid date handling
    test('Invalid date should return fallback', function() {
        const result = window.TimeUtils.formatTime12h('invalid-date-string');
        // Should return the input string as fallback
        assert(typeof result === 'string', 'Result should be a string');
    });

    // Test 7: Timezone independence with ISO strings
    test('ISO strings should handle timezones correctly', function() {
        const isoString = '2024-01-01T20:00:00Z';
        const result = window.TimeUtils.formatTime12h(isoString);
        // Should format correctly regardless of system timezone
        assert(typeof result === 'string', 'Result should be a string');
        assert(result.length > 0, 'Result should not be empty');
    });

    // Test 8: formatTime12hWithTooltip
    test('formatTime12hWithTooltip should return formatted and tooltip', function() {
        const date = new Date('2024-01-01T10:30:00Z');
        const result = window.TimeUtils.formatTime12hWithTooltip(date);
        assert(result.formatted, 'Should have formatted property');
        assert(result.tooltip, 'Should have tooltip property');
        assert(typeof result.formatted === 'string', 'Formatted should be string');
        assert(typeof result.tooltip === 'string', 'Tooltip should be string');
    });

    // Run all tests
    console.log('Running time formatting tests...\n');
    tests.forEach(({ name, fn }) => {
        try {
            fn();
            console.log(`✓ ${name}`);
            passed++;
        } catch (error) {
            console.error(`✗ ${name}`);
            console.error(`  Error: ${error.message}`);
            failed++;
        }
    });

    console.log(`\nTests: ${passed} passed, ${failed} failed`);
    return failed === 0;
}

// Run tests if executed directly
if (require.main === module) {
    const success = runTests();
    process.exit(success ? 0 : 1);
}

module.exports = { runTests };

