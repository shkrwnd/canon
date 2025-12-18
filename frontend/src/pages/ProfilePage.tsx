import React, { useState } from "react";
import { Header } from "../components/shared";
import { Button, Input } from "../components/ui";
import { formatDate } from "../utils/formatters";

export const ProfilePage: React.FC = () => {
  const [isEditing, setIsEditing] = useState(false);
  
  // Mock user data - in real app, this would come from an API
  // For now, we'll get email from token or use a placeholder
  const [userData, setUserData] = useState({
    email: "user@example.com", // This would come from API
    createdAt: new Date().toISOString(),
  });
  
  const [formData, setFormData] = useState({
    email: userData.email,
  });

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({ email: userData.email });
  };

  const handleCancel = () => {
    setIsEditing(false);
    setFormData({ email: userData.email });
  };

  const handleSave = async () => {
    // TODO: Implement API call to update user profile
    // For now, just update local state
    setUserData({ ...userData, email: formData.email });
    setIsEditing(false);
    // In real implementation:
    // await updateUserProfile(formData);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header />

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Account Information</h2>
            {!isEditing && (
              <Button variant="outline" size="sm" onClick={handleEdit}>
                Edit Profile
              </Button>
            )}
          </div>

          {isEditing ? (
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Enter your email"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Note: Email updates will require verification
                </p>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={handleSave}>
                  Save Changes
                </Button>
                <Button variant="outline" onClick={handleCancel}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Email Address
                </label>
                <p className="text-base text-gray-900">{userData.email}</p>
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
          )}
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

