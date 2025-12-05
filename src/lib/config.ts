export const DASHBOARD_CONFIG = {
    countries: ['ALL', 'US', 'KR', 'CN', 'JP'],
    comingSoonCountries: ['EU', 'CRYPTO'],
    categories: ['ALL', 'ECONOMY', 'POLITICS', 'SOCIETY', 'TECH'],
    countryFlags: {
        'US': '🇺🇸',
        'KR': '🇰🇷',
        'CN': '🇨🇳',
        'JP': '🇯🇵',
        'EU': '🇪🇺',
        'UK': '🇬🇧',
        'CRYPTO': '🪙',
        'ALL': '🌍'
    } as Record<string, string>,
    refreshInterval: 60000, // 1 minute
    minImportanceScore: 6,
    scanRangeDays: 7
}

export function getCountryFlag(country: string) {
    return DASHBOARD_CONFIG.countryFlags[country] || '🌍'
}
