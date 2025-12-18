import { validateEmail, validatePassword, validateModuleName } from "./validators";

export const validateLoginForm = (email: string, password: string): { valid: boolean; errors: Record<string, string> } => {
  const errors: Record<string, string> = {};

  if (!email || !validateEmail(email)) {
    errors.email = "Please enter a valid email address";
  }

  if (!password || password.length === 0) {
    errors.password = "Password is required";
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
};

export const validateRegisterForm = (email: string, password: string, confirmPassword: string): { valid: boolean; errors: Record<string, string> } => {
  const errors: Record<string, string> = {};

  if (!email || !validateEmail(email)) {
    errors.email = "Please enter a valid email address";
  }

  const passwordValidation = validatePassword(password);
  if (!password || !passwordValidation.valid) {
    errors.password = passwordValidation.error || "Password is required";
  }

  if (password !== confirmPassword) {
    errors.confirmPassword = "Passwords do not match";
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
};

export const validateModuleForm = (name: string): { valid: boolean; errors: Record<string, string> } => {
  const errors: Record<string, string> = {};

  const nameValidation = validateModuleName(name);
  if (!nameValidation.valid) {
    errors.name = nameValidation.error || "Module name is required";
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
};

