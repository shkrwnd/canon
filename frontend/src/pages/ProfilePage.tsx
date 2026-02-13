import React, { useState, useEffect } from "react";
import { Header } from "../components/shared";
import { Button } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { formatDate } from "../utils/formatters";

export const ProfilePage: React.FC = () => {
  const { userEmail } = useAuth();
  const [userData, setUserData] = useState({
    email: userEmail ?? "",
    createdAt: new Date().toISOString(),
  });

  useEffect(() => {
    if (userEmail) {
      setUserData((prev) => ({ ...prev, email: userEmail }));
    }
  }, [userEmail]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header />

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Account Information</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                Email Address
              </label>
              <p className="text-base text-gray-900">{userData.email}</p>
              <p className="mt-1 text-xs text-gray-500">
                Email cannot be changed
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                Account Created
              </label>
              <p className="text-base text-gray-900">
                {formatDate(userData.createdAt)}
              </p>
            </div>
          </div>
        </div>

        {/* Additional Sections */}
        <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Account Settings</h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Change Password</h3>
                <p className="text-sm text-gray-500">Update your password to keep your account secure</p>
              </div>
              <Button variant="outline" size="sm" disabled>
                Coming Soon
              </Button>
            </div>

            <div className="flex items-center justify-between py-3 border-b">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Delete Account</h3>
                <p className="text-sm text-gray-500">Permanently delete your account and all data</p>
              </div>
              <Button variant="outline" size="sm" disabled>
                Coming Soon
              </Button>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-red-200 p-6">
          <h2 className="text-xl font-semibold text-red-900 mb-4">Danger Zone</h2>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-900">Logout</h3>
              <p className="text-sm text-gray-500">Sign out of your account</p>
            </div>
            <p className="text-sm text-gray-500">Use the logout button in the header</p>
          </div>
        </div>
        </div>
      </div>
    </div>
  );
};

