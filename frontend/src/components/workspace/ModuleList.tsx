import React, { useState } from "react";
import { useModules, useCreateModule, useDeleteModule } from "../../hooks/useModules";
import { Module } from "../../types";
import { Button, Input } from "../ui";
import { validateModuleForm } from "../../utils/validation.utils";

interface ModuleListProps {
  selectedModuleId: number | null;
  onSelectModule: (module: Module | null) => void;
  showCreateForm?: boolean;
  onShowCreateFormChange?: (show: boolean) => void;
}

export const ModuleList: React.FC<ModuleListProps> = ({ 
  selectedModuleId, 
  onSelectModule,
  showCreateForm: externalShowCreateForm,
  onShowCreateFormChange,
}) => {
  const { data: modules, isLoading } = useModules();
  const createModule = useCreateModule();
  const deleteModule = useDeleteModule();
  const [internalShowCreateForm, setInternalShowCreateForm] = useState(false);
  const [newModuleName, setNewModuleName] = useState("");

  // Use external state if provided, otherwise use internal state
  const showCreateForm = externalShowCreateForm !== undefined ? externalShowCreateForm : internalShowCreateForm;
  const setShowCreateForm = (value: boolean) => {
    if (onShowCreateFormChange) {
      onShowCreateFormChange(value);
    } else {
      setInternalShowCreateForm(value);
    }
  };

  const handleCreate = async () => {
    const validation = validateModuleForm(newModuleName);
    if (!validation.valid) {
      alert(validation.errors.name);
      return;
    }

    try {
      const module = await createModule.mutateAsync({
        name: newModuleName,
        standing_instruction: "",
        content: "",
      });
      setNewModuleName("");
      setShowCreateForm(false);
      onSelectModule(module);
    } catch (error: any) {
      alert(error.response?.data?.detail || "Failed to create module");
    }
  };

  const handleDelete = async (e: React.MouseEvent, moduleId: number) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this module?")) {
      await deleteModule.mutateAsync(moduleId);
      if (selectedModuleId === moduleId) {
        onSelectModule(null);
      }
    }
  };

  if (isLoading) {
    return <div className="p-4">Loading modules...</div>;
  }

  return (
    <div className="flex flex-col h-full border-r">
      <div className="p-4 border-b">
        <Button
          data-create-module
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="w-full"
          size="sm"
        >
          {showCreateForm ? "Cancel" : "+ New Module"}
        </Button>
        {showCreateForm && (
          <div className="mt-2 space-y-2">
            <Input
              data-module-name-input
              placeholder="Module name"
              value={newModuleName}
              onChange={(e) => setNewModuleName(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleCreate()}
            />
            <Button onClick={handleCreate} className="w-full" size="sm" disabled={createModule.isPending}>
              Create
            </Button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto">
        {modules && modules.length === 0 ? (
          <div className="p-4 text-sm text-gray-500 text-center">
            No modules yet. Create one to get started.
          </div>
        ) : (
          <div className="divide-y">
            {modules?.map((module) => (
              <div
                key={module.id}
                onClick={() => onSelectModule(module)}
                className={`p-4 cursor-pointer hover:bg-gray-50 ${
                  selectedModuleId === module.id ? "bg-blue-50 border-l-4 border-blue-600" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{module.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {module.content ? `${module.content.length} chars` : "Empty"}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, module.id)}
                    className="ml-2 text-red-500 hover:text-red-700 text-xs"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};



