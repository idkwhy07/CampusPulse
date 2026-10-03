const loginForm = document.getElementById('loginForm');
const loginEmail = document.getElementById('loginEmail');
const loginPassword = document.getElementById('loginPassword');
const loginError = document.getElementById('loginError');
const loginBtn = document.getElementById('loginBtn');

const existingUser = CampusPulseAPI.getUser();
if (CampusPulseAPI.getToken() && existingUser) {
  window.location.replace(CampusPulseAPI.homeFor(existingUser));
}

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginError.textContent = '';
  const email = loginEmail.value.trim();
  const password = loginPassword.value;
  if (!email || !password) {
    loginError.textContent = 'Vui lòng nhập email và mật khẩu.';
    return;
  }

  loginBtn.disabled = true;
  try {
    const data = await CampusPulseAPI.login(email, password);
    window.location.replace(CampusPulseAPI.homeFor(data.user));
  } catch (error) {
    loginError.textContent = error.message || 'Đăng nhập thất bại.';
  } finally {
    loginBtn.disabled = false;
  }
});
