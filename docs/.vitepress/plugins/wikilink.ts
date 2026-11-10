// 把 Obsidian 的 [[笔记名]] / [[路径|别名]] 渲染成行内代码。
// 只影响 VitePress 的输出；Obsidian 源文件保持原样，WikiLink 仍然可用。
// 不生成链接的原因：被引用的课程笔记位于 docs/ 之外，站点里没有对应页面。
export function wikilinkPlugin(md: any): void {
  md.inline.ruler.before('link', 'wikilink', (state: any, silent: boolean) => {
    const start = state.pos
    const src = state.src

    if (src.charCodeAt(start) !== 0x5b || src.charCodeAt(start + 1) !== 0x5b) {
      return false
    }

    const end = src.indexOf(']]', start + 2)
    if (end === -1) return false

    const raw = src.slice(start + 2, end)
    if (!raw || raw.includes('\n') || raw.includes('[[') || raw.includes(']]')) {
      return false
    }

    const [targetPart, aliasPart] = raw.split('|', 2)
    const target = targetPart.trim()
    if (!target) return false

    if (!silent) {
      const token = state.push('wikilink', '', 0)
      token.content = (aliasPart || target).trim()
      token.meta = { target }
    }

    state.pos = end + 2
    return true
  })

  md.renderer.rules.wikilink = (tokens: any[], idx: number): string => {
    const token = tokens[idx]
    const text = md.utils.escapeHtml(token.content)
    const target = md.utils.escapeHtml(token.meta?.target ?? '')
    return `<code class="wikilink" title="Obsidian 内部链接：${target}（原笔记不在本站内）">${text}</code>`
  }
}
