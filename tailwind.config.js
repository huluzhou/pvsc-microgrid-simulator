/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 工作模式颜色
        'mode-random': '#3b82f6', // 蓝色 - 随机数据模式
        'mode-manual': '#10b981', // 绿色 - 手动模式
        'mode-remote': '#f59e0b', // 橙色 - 远程模式
        'mode-historical': '#a855f7', // 紫色 - 历史数据模式
      },
    },
  },
  plugins: [],
  darkMode: 'class',
}
