// 主题状态管理 - 统一浅色主题
// 移除了主题切换功能，固定使用浅色主题

export const THEME = 'light' as const;

// 确保移除 dark class
if (typeof window !== 'undefined') {
  document.documentElement.classList.remove('dark');
}
