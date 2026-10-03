const registerForm = document.getElementById('registerForm');
const registerName = document.getElementById('registerName');
const registerEmail = document.getElementById('registerEmail');
const registerPassword = document.getElementById('registerPassword');
const registerConfirm = document.getElementById('registerConfirm');
const registerError = document.getElementById('registerError');
const registerBtn = document.getElementById('registerBtn');

const existingUser = CampusPulseAPI.getUser();
if (CampusPulseAPI.getToken() && existingUser) {
  window.location.replace(CampusPulseAPI.homeFor(existingUser));
}

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  registerError.textContent = '';

  const name = registerName.value.trim();
  const email = registerEmail.value.trim();
  const password = registerPassword.value;
  const confirm = registerConfirm.value;

  if (name.length < 2) {
    registerError.textContent = 'Họ tên phải có ít nhất 2 ký tự.';
    return;
  }
  if (password.length < 6) {
    registerError.textContent = 'Mật khẩu phải có ít nhất 6 ký tự.';
    return;
  }
  if (password !== confirm) {
    registerError.textContent = 'Hai mật khẩu không khớp.';
    return;
  }

  registerBtn.disabled = true;
  try {
    await CampusPulseAPI.register(name, email, password);
    window.location.replace('/');
  } catch (error) {
    registerError.textContent = error.message || 'Đăng ký thất bại.';
  } finally {
    registerBtn.disabled = false;
  }
});
