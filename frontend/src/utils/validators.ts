export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePassword = (password: string): { valid: boolean; error?: string } => {
  if (password.length < 8) {
    return { valid: false, error: "Password must be at least 8 characters long" };
  }
  return { valid: true };
};

export const validateName = (name: string, entityType: string = "name"): { valid: boolean; error?: string } => {
  if (!name || name.trim().length === 0) {
    return { valid: false, error: `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} is required` };
  }
  if (name.length > 100) {
    return { valid: false, error: `${entityType.charAt(0).toUpperCase() + entityType.slice(1)} must be less than 100 characters` };
  }
  return { valid: true };
};

// Legacy alias for backward compatibility (can be removed later)
export const validateModuleName = (name: string): { valid: boolean; error?: string } => {
  return validateName(name, "name");
};



