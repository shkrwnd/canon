import React, { useState } from "react";
import { Button, Input } from "../ui";
import { validateLoginForm, validateRegisterForm } from "../../utils/validation.utils";
import { UserLogin, UserRegister } from "../../types";

interface AuthFormProps {
  mode: "login" | "register";
  onSubmit: (data: UserLogin | UserRegister) => Promise<void>;
  onToggleMode: () => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ mode, onSubmit, onToggleMode }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    let validation;
    if (mode === "login") {
      validation = validateLoginForm(email, password);
    } else {
      validation = validateRegisterForm(email, password, confirmPassword);
    }

    if (!validation.valid) {
      setErrors(validation.errors);
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await onSubmit({ email, password });
      } else {
        await onSubmit({ email, password });
      }
    } catch (error: any) {
      setErrors({ submit: error.response?.data?.detail || "An error occurred" });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
          Email
        </label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email}</p>}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
          Password
        </label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />
        {errors.password && <p className="mt-1 text-sm text-red-600">{errors.password}</p>}
      </div>

      {mode === "register" && (
        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
            Confirm Password
          </label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
          />
          {errors.confirmPassword && <p className="mt-1 text-sm text-red-600">{errors.confirmPassword}</p>}
        </div>
      )}

      {errors.submit && <p className="text-sm text-red-600">{errors.submit}</p>}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Loading..." : mode === "login" ? "Login" : "Register"}
      </Button>

      <div className="text-center text-sm text-gray-600">
        {mode === "login" ? (
          <>
            Don't have an account?{" "}
            <button type="button" onClick={onToggleMode} className="text-blue-600 hover:underline">
              Register
            </button>
          </>
        ) : (
          <>
            Already have an account?{" "}
            <button type="button" onClick={onToggleMode} className="text-blue-600 hover:underline">
              Login
            </button>
          </>
        )}
      </div>
    </form>
  );
};



