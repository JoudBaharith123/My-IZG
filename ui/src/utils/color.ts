export function colorFromString(value: string, index: number = 0): string {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i)
    hash |= 0
  }
  const hue = Math.abs(hash + index * 37) % 360
  const saturation = 70
  const lightness = 50
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`
}
