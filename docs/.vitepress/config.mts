import { defineConfig, type DefaultTheme } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { wikilinkPlugin } from './plugins/wikilink'

// 站点根目录 = docs/。
// package.json 里的 scripts 固定以 `vitepress <command> docs` 调用，
// 因此 local-materials/、personal-notes/、90-原始PDF/ 等私有目录不会进入构建。
// 首次本地预览前先执行 `npm install`。
//
// 关于 URL 中的中文：曾尝试用 rewrites 把中文路径映射成英文，但 VitePress 的
// 相对链接按「改写后的路径」解析，docs/ 内 166 条 `./00-领域总览.md` 形式的链接
// 会全部变成死链（实测 121 条）。改这些链接会破坏 Obsidian 内的跳转，
// 与本项目「不批量改笔记」的约定冲突，因此放弃 rewrites，保留中文 URL。

type Domain = {
  /** 领域编号，如 "10" */
  id: string
  /** 领域名称，如 "数学基础" */
  name: string
  /** docs/ 下的目录名 */
  dir: string
  /** 是否存在 03-已有笔记索引.md */
  notesIndex?: boolean
}

const domains: Domain[] = [
  { id: '10', name: '数学基础', dir: '10-数学基础' },
  { id: '20', name: '编程基础', dir: '20-编程基础' },
  { id: '30', name: '数据结构与算法', dir: '30-数据结构与算法', notesIndex: true },
  { id: '40', name: '计算机组成', dir: '40-计算机组成', notesIndex: true },
  { id: '50', name: '操作系统', dir: '50-操作系统' },
  { id: '60', name: '计算机网络', dir: '60-计算机网络' },
  { id: '70', name: '数据库', dir: '70-数据库', notesIndex: true },
  { id: '80', name: '编译原理', dir: '80-编译原理' },
  { id: '90', name: '软件工程', dir: '90-软件工程', notesIndex: true },
  { id: '100', name: '前端开发', dir: '100-前端开发' },
  { id: '110', name: '后端开发', dir: '110-后端开发' },
  { id: '120', name: '软件安全', dir: '120-软件安全' },
  { id: '130', name: 'DevOps与运维', dir: '130-DevOps与运维' },
  { id: '140', name: '分布式系统', dir: '140-分布式系统' },
  { id: '150', name: '系统架构', dir: '150-系统架构' },
  { id: '160', name: '计算机高级选修', dir: '160-计算机高级选修' },
]

function domainItems(domain: Domain): DefaultTheme.SidebarItem[] {
  const base = `/${domain.dir}`
  const items: DefaultTheme.SidebarItem[] = [
    { text: '领域总览', link: `${base}/00-领域总览` },
    { text: '知识点目录', link: `${base}/01-知识点目录` },
    { text: '权威课程与资料', link: `${base}/02-权威课程与资料` },
  ]
  if (domain.notesIndex) {
    items.push({ text: '已有笔记索引', link: `${base}/03-已有笔记索引` })
  }
  if (domain.dir === '30-数据结构与算法') {
    items.push({ text: '算法设计范式', link: `${base}/04-算法设计范式` })
  }
  return items
}

const domainNavItems = domains.map((domain) => ({
  text: `${domain.id} · ${domain.name}`,
  link: `/${domain.dir}/00-领域总览`,
}))

const domainSidebar: DefaultTheme.SidebarItem[] = domains.map((domain) => ({
  text: `${domain.id} · ${domain.name}`,
  collapsed: false,
  items: domainItems(domain),
}))

export default withMermaid(
  defineConfig({
    lang: 'zh-CN',
    title: '计算机科学学习笔记',
    description: '16 个知识领域的原创中文笔记与公开课程索引；不含第三方 PDF。',

    // 将来发布到 GitHub Pages 项目页时，取消下一行注释，并把仓库名对齐：
    // base: '/computer-science-learning/',

    markdown: {
      lineNumbers: true,
      config: (md) => {
        // 把 Obsidian 的 [[笔记名]] 渲染成行内代码，避免站点里出现裸的双括号。
        md.use(wikilinkPlugin)
      },
    },

    // docs/ 中少量页面链接到仓库根目录（站点之外）的文件，例如
    // ../sources/03-许可判定规则.md 与 ../02-课程总览.md。
    // 这些链接在站点里不可达（VitePress 会把它们归一化成 ./../xxx），
    // 构建时忽略「跳出 docs/」的链接；docs/ 内部的死链仍会被检查。
    ignoreDeadLinks: [/^(\.\/)?\.\.\//],

    themeConfig: {
      nav: [
        { text: '知识地图', link: '/00-知识地图' },
        { text: '学习路径', link: '/01-学习路径' },
        { text: '16 个领域', items: domainNavItems },
      ],

      sidebar: [
        {
          text: '总纲',
          items: [
            { text: '计算机科学知识地图', link: '/00-知识地图' },
            { text: '学习路径', link: '/01-学习路径' },
          ],
        },
        ...domainSidebar,
      ],

      outline: { level: [2, 3], label: '本页目录' },
      search: { provider: 'local' },
      docFooter: { prev: '上一篇', next: '下一篇' },
      lastUpdated: { text: '最后更新' },

      darkModeSwitchLabel: '外观',
      lightModeSwitchTitle: '切换到浅色模式',
      darkModeSwitchTitle: '切换到深色模式',
      sidebarMenuLabel: '目录',
      returnToTopLabel: '回到顶部',
      langMenuLabel: '语言',

      footer: {
        message: '原创内容；第三方课程资料仅登记链接，不随站点分发。',
      },
    },
  }),
)
