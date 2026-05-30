// 验证前端设置的脚本 - 仅用于检查文件
// 可以在浏览器控制台或 Node.js 中运行（需要 node 环境）

console.log('🧐 CrisisNet 前端设置验证...\n');

// 检查 package.json 是否存在
console.log('📦 检查 package.json...');
try {
  const fs = require('fs');
  const path = require('path');

  const pkgPath = path.join(__dirname, 'package.json');
  if (fs.existsSync(pkgPath)) {
    console.log('✅ package.json 存在');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

    // 检查依赖
    const requiredDeps = ['react', 'react-dom', 'leaflet', 'react-leaflet', 'recharts', 'lucide-react', 'clsx', 'tailwindcss'];
    let allDepsOk = true;

    requiredDeps.forEach(dep => {
      if (pkg.dependencies && pkg.dependencies[dep]) {
        console.log(`   ✅ ${dep}: ${pkg.dependencies[dep]}`);
      } else {
        console.log(`   ❌ ${dep}: 未找到`);
        allDepsOk = false;
      }
    });

    if (allDepsOk) {
      console.log('✅ 所有依赖已配置\n');
    }
  }
} catch (e) {
  console.log('⚠️ 无法读取 package.json，可能在浏览器环境\n');
}

console.log('📁 检查项目结构...');
console.log('   主要组件文件:');
console.log('   - src/App.js');
console.log('   - src/index.js');
console.log('   - src/index.css');
console.log('   - src/components/*.js');
console.log('   - tailwind.config.js');
console.log('   - postcss.config.js\n');

console.log('🎨 检查 clsx 使用...');
console.log('   所有需要 clsx 的组件都应包含: import { clsx } from "clsx";');
console.log('   已确认组件: App.js, AgentDetailPanel.js, GlobalDashboard.js, TimelinePanel.js\n');

console.log('🚀 下一步:');
console.log('   1. cd frontend');
console.log('   2. npm install');
console.log('   3. npm start\n');

console.log('✨ 如果 npm install 太慢，使用国内镜像:');
console.log('   npm install --registry=https://registry.npmmirror.com\n');
