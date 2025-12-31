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
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
          Email
        </label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        {errors.email && <p className="mt-1.5 text-sm text-red-600 font-medium">{errors.email}</p>}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
          Password
        </label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />
        {errors.password && <p className="mt-1.5 text-sm text-red-600 font-medium">{errors.password}</p>}
      </div>

      {mode === "register" && (
        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-semibold text-gray-700 mb-2">
            Confirm Password
          </label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
          />
          {errors.confirmPassword && <p className="mt-1.5 text-sm text-red-600 font-medium">{errors.confirmPassword}</p>}
        </div>
      )}

      {errors.submit && (
        <div className="p-3 bg-red-50 border-2 border-red-200 rounded-lg">
          <p className="text-sm text-red-700 font-medium">{errors.submit}</p>
        </div>
      )}

      <Button type="submit" className="w-full mt-6" disabled={isSubmitting} size="lg">
        {isSubmitting ? "Loading..." : mode === "login" ? "Sign In" : "Create Account"}
      </Button>

      <div className="text-center text-sm text-gray-600 pt-2">
        {mode === "login" ? (
          <>
            Don't have an account?{" "}
            <button type="button" onClick={onToggleMode} className="text-blue-600 hover:text-blue-700 font-semibold hover:underline transition-colors">
              Register
            </button>
          </>
        ) : (
          <>
            Already have an account?{" "}
            <button type="button" onClick={onToggleMode} className="text-blue-600 hover:text-blue-700 font-semibold hover:underline transition-colors">
              Sign In
            </button>
          </>
        )}
      </div>
    </form>
  );
};



