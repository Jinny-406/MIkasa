import { stringWidth } from '@hermes/ink'
import { describe, expect, it } from 'vitest'

import { busyIndicatorWidth, renderIndicator } from '../components/appChrome.js'
import { minimalBannerText } from '../components/minimalBanner.js'
import { fromSkin } from '../theme.js'

describe('minimal theme behavior', () => {
  it('carries skin branding into a header that fits narrow and wide terminals', () => {
    const branding = { agent_name: 'Mikasa', banner_style: 'minimal', icon: '○', tagline: 'PERSONAL AGENT' }
    const theme = fromSkin({ background: '#101112', banner_text: '#F0F0EE' }, branding)
    expect(theme.brand.bannerStyle).toBe(branding.banner_style)
    expect(theme.brand.icon).toBe(branding.icon)
    for (const columns of [1, 12, 32, 58, 100]) {
      const header = minimalBannerText(theme.brand.name, theme.brand.tagline!, '0.21.0', columns)
      expect(stringWidth(header.wordmark + header.label + header.release)).toBeLessThanOrEqual(columns)
      expect(header.wordmark.length).toBeGreaterThan(0)
    }
  })

  it('animates the pulse without changing the width reserved for status content', () => {
    const frames = Array.from({ length: 32 }, (_, tick) => renderIndicator('pulse', tick))
    expect(new Set(frames.map(frame => frame.frame)).size).toBeGreaterThan(1)
    expect(new Set(frames.map(frame => stringWidth(frame.frame))).size).toBe(1)
    expect(frames.every(frame => frame.intervalMs > 0)).toBe(true)
    expect(busyIndicatorWidth('pulse', true)).toBeGreaterThan(busyIndicatorWidth('pulse', false))
    expect(busyIndicatorWidth('pulse', false)).toBeGreaterThan(stringWidth(frames[0]!.frame))
  })
})
