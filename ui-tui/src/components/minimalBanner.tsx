import { Box, stringWidth, Text } from '@hermes/ink'

import type { Theme } from '../theme.js'

export function minimalBannerText(name: string, tagline: string, version: string, columns: number) {
  const width = Math.max(1, columns)
  const plain = name.replace(/\s+agent$/i, '').toUpperCase()
  const spaced = [...plain].join('  ')
  const wordmark = stringWidth(spaced) <= width ? spaced : [...plain].slice(0, width).join('')
  const suffix = version ? ` / v${version}` : ''
  const description = tagline ? `  ○  ${tagline}` : ''
  const label = stringWidth(wordmark + description + suffix) <= width ? description : ''
  const release = stringWidth(wordmark + label + suffix) <= width ? suffix : ''

  return { label, release, width, wordmark }
}

export function MinimalBanner({ columns, t, version = '' }: { columns: number; t: Theme; version?: string }) {
  const text = minimalBannerText(t.brand.name, t.brand.tagline ?? '', version, columns)

  return (
    <Box flexDirection="column" marginBottom={1} width={text.width}>
      <Text wrap="truncate-end">
        <Text color={t.color.primary}>{text.wordmark}</Text>
        <Text color={t.color.muted}>
          {text.label}
          {text.release}
        </Text>
      </Text>
      <Text color={t.color.border}>{'─'.repeat(text.width)}</Text>
    </Box>
  )
}
