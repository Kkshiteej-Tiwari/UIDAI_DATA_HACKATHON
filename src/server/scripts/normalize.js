/**
 * State/District Name Normalization Utilities
 * Handles aliases, case normalization, and trimming
 */

// State name aliases (map to canonical names)
const STATE_ALIASES = {
    'ORISSA': 'ODISHA',
    'UTTARANCHAL': 'UTTARAKHAND',
    'NCT OF DELHI': 'DELHI',
    'DADRA AND NAGAR HAVELI': 'DADRA AND NAGAR HAVELI AND DAMAN AND DIU',
    'DAMAN AND DIU': 'DADRA AND NAGAR HAVELI AND DAMAN AND DIU',
    'PONDICHERRY': 'PUDUCHERRY'
};

/**
 * Normalize state name
 * - Uppercase
 * - Trim whitespace
 * - Apply aliases
 */
function normalizeStateName(state) {
    if (!state || typeof state !== 'string') {
        return null;
    }

    let normalized = state.toUpperCase().trim();

    // Remove extra whitespace
    normalized = normalized.replace(/\s+/g, ' ');

    // Apply aliases
    if (STATE_ALIASES[normalized]) {
        normalized = STATE_ALIASES[normalized];
    }

    return normalized;
}

/**
 * Normalize district name
 * - Uppercase
 * - Trim whitespace
 */
function normalizeDistrictName(district) {
    if (!district || typeof district !== 'string') {
        return null;
    }

    let normalized = district.toUpperCase().trim();

    // Remove extra whitespace
    normalized = normalized.replace(/\s+/g, ' ');

    return normalized;
}

/**
 * Validate and parse numeric value
 * Returns null if invalid
 */
function parseNumericValue(value) {
    if (value === null || value === undefined || value === '') {
        return 0;
    }

    const parsed = parseInt(value, 10);

    if (isNaN(parsed) || parsed < 0) {
        return 0;
    }

    return parsed;
}

/**
 * Parse date from various formats
 */
function parseDate(dateStr) {
    if (!dateStr || typeof dateStr !== 'string') {
        return null;
    }

    // Try DD-MM-YYYY format
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        const day = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);
        const year = parseInt(parts[2], 10);

        if (!isNaN(day) && !isNaN(month) && !isNaN(year)) {
            return {
                date: dateStr,
                month: `${year}-${String(month).padStart(2, '0')}`,
                year: year
            };
        }
    }

    return {
        date: dateStr,
        month: null,
        year: null
    };
}

module.exports = {
    normalizeStateName,
    normalizeDistrictName,
    parseNumericValue,
    parseDate,
    STATE_ALIASES
};
