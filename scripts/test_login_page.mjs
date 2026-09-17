import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/Users/mac/.nvm/versions/node/v24.13.0/lib/node_modules/playwright');

async function testLoginPage() {
  console.log('🚀 开始自动化端到端测试登录页面...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();
  page.on('console', msg => console.log('   [Browser Console]', msg.text()));
  page.on('response', resp => {
    if (resp.url().includes('/api/v1/auth/login')) {
      console.log('   [Auth Response Status]', resp.status());
    }
  });

  // 清理可能已有的登录状态以确保显示登录页
  await page.goto('http://localhost:6002/');
  await page.evaluate(() => {
    localStorage.clear();
  });
  await page.reload();
  await page.waitForTimeout(1000);

  console.log('1. 验证登录页面渲染...');
  const title = await page.locator('h1').textContent();
  console.log('   页面标题:', title);
  if (!title.includes('AgentForge')) {
    throw new Error('未正确加载 AgentForge 登录页');
  }

  // 截图初始登录页
  await page.screenshot({ path: 'login_initial.png' });
  console.log('   📸 初始登录页截图保存: login_initial.png');

  console.log('2. 验证记住密码复选框与密码输入框右侧眼睛图标交互...');
  const rememberText = await page.locator('text=记住密码');
  if (!(await rememberText.isVisible())) {
    throw new Error('未找到记住密码元素');
  }
  console.log('   ✅ 记住密码复选框存在');

  // 验证密码输入框右侧的眼睛图标
  const eyeBtn = page.locator('button[title="显示密码"]');
  if (!(await eyeBtn.isVisible())) {
    throw new Error('未在密码输入框右侧找到显示密码眼睛图标');
  }
  const passInput = page.locator('input[placeholder="请输入密码"]');
  console.log('   初始密码输入框类型:', await passInput.getAttribute('type'));
  await eyeBtn.click();
  await page.waitForTimeout(200);
  const passTypeAfterClick = await passInput.getAttribute('type');
  console.log('   点击眼睛后密码输入框类型:', passTypeAfterClick);
  if (passTypeAfterClick !== 'text') {
    throw new Error('点击眼睛图标后密码未切换为明文 text');
  }
  // 再次点击切回密文
  await page.locator('button[title="隐藏密码"]').click();
  await page.waitForTimeout(200);
  if (await passInput.getAttribute('type') !== 'password') {
    throw new Error('再次点击眼睛图标后密码未切回 password 密文');
  }
  console.log('   ✅ 密码输入框右侧眼睛图标切换功能验证通过！');

  console.log('3. 验证未通过图形验证码时的拦截提示...');
  // 点击快速填入管理员
  await page.locator('button:has-text("管理员")').click();
  await page.locator('button:has-text("登录进入实战台")').click();
  await page.waitForTimeout(500);
  const errorText = await page.locator('text=请先点击选择最小图形完成人机安全验证').textContent();
  console.log('   拦截提示成功:', errorText);

  console.log('4. 验证图形验证码交互与最小图形识别...');
  const buttons = page.locator('[data-testid="captcha-shape-item"]');
  const count = await buttons.count();
  console.log('   图形候选按钮数量:', count);
  if (count !== 4) {
    throw new Error(`图形验证码候选应为 4 个，实际为: ${count}`);
  }

  // 找出非最小图形进行错误分支测试
  const notSmallestBtn = page.locator('[data-testid="captcha-shape-item"][data-is-smallest="false"]').first();
  console.log('   故意点击较大图形测试错误拦截...');
  await notSmallestBtn.click();
  await page.waitForTimeout(300);

  const wrongMsg = await page.locator('text=选择错误').textContent();
  console.log('   错误反馈已正确提示:', wrongMsg);

  // 等待验证码自动刷新重置 (700ms)
  await page.waitForTimeout(1000);

  // 点击最小图形完成验证
  const smallestBtn = page.locator('[data-testid="captcha-shape-item"][data-is-smallest="true"]');
  console.log('   点击最小图形...');
  await smallestBtn.click();
  await page.waitForTimeout(500);

  const passMsg = await page.locator('text=人机安全检验已确认').textContent();
  console.log('   ✅ 验证码通过提示:', passMsg);
  await page.screenshot({ path: 'captcha_verified.png' });
  console.log('   📸 验证码通过截图保存: captcha_verified.png');

  console.log('5. 提交登录并验证记住密码...');
  await page.locator('button:has-text("登录进入实战台")').click();
  await page.waitForTimeout(1500);

  // 检查是否进入主工作台 (通过检查页面文本中是否包含工作台关键标识)
  const isWorkbenchPresent = await page.evaluate(() => {
    return document.querySelector('.wb-layout') !== null;
  });
  console.log('   工作台是否登录成功展示:', isWorkbenchPresent);
  if (!isWorkbenchPresent) {
    throw new Error('登录失败未进入工作台');
  }

  // 检查 localStorage 是否保存了记住密码
  const remembered = await page.evaluate(() => localStorage.getItem('agentforge_remembered_creds'));
  console.log('   localStorage 保存的记住凭据:', remembered);
  if (!remembered || !remembered.includes('admin')) {
    throw new Error('记住密码未能成功持久化到 localStorage');
  }

  await page.screenshot({ path: 'workbench_logged_in.png' });
  console.log('   📸 登录成功工作台截图保存: workbench_logged_in.png');

  console.log('6. 验证登出后自动回填记住的账号密码...');
  // 清除会话 token 模拟登出，保留记住的凭据
  await page.evaluate(() => localStorage.removeItem('agentforge_jwt_token'));
  await page.reload();
  await page.waitForTimeout(1000);

  const filledUser = await page.locator('input[placeholder*="请输入用户名"]').inputValue();
  const filledPass = await page.locator('input[placeholder*="请输入密码"]').inputValue();
  console.log('   重新进入登录页自动回填用户名:', filledUser, '密码长度:', filledPass.length);
  if (filledUser !== 'admin' || !filledPass) {
    throw new Error('记住密码未能成功自动回填到输入框');
  }
  console.log('   ✅ 记住密码自动回填验证成功！');

  await browser.close();
  console.log('🎉 所有自动化验证全部 100% 通过！');
}

testLoginPage().catch(err => {
  console.error('❌ 测试失败:', err);
  process.exit(1);
});
