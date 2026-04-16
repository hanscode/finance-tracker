/**
 * Finance Tracker — Main App Component
 *
 * 💡 CONCEPT: React Components
 *    In Flask, you rendered HTML with Jinja2 templates.
 *    In React, each piece of UI is a "component" — a function
 *    that returns JSX (HTML inside JavaScript).
 *
 *    This component does 2 things:
 *    1. Displays the main interface
 *    2. Fetches the backend (/api/health) to verify the connection
 *
 * 💡 CONCEPT: useState and useEffect (React Hooks)
 *    - useState: stores data that changes (like variables in Python, but React
 *      re-renders the UI when they change)
 *    - useEffect: runs code when the component mounts (like __init__
 *      in a Python class)
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// TypeScript interface — defines the shape of the health check data
// Similar to a Pydantic schema but for the frontend
interface HealthStatus {
  status: string;
  app: string;
  version: string;
}

function App() {
  // useState<T | null>(null) — starts as null, then becomes HealthStatus
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // useEffect with [] — runs ONCE when the component mounts
  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data: HealthStatus) => setHealth(data))
      .catch((err: Error) => setError(err.message));
  }, []); // ← [] means "run only on mount"

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">
            💰 Finance Tracker
          </CardTitle>
          <CardDescription>
            Your money. Your server. Your privacy.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Backend connection status */}
          <div className="rounded-lg border p-4">
            <p className="text-sm font-medium mb-2">Backend Status</p>
            {error ? (
              <p className="text-sm text-destructive">
                ❌ Error: {error}
              </p>
            ) : health ? (
              <div className="text-sm space-y-1">
                <p className="text-green-600 dark:text-green-400">
                  ✅ {health.app} v{health.version}
                </p>
                <p className="text-muted-foreground">
                  Status: {health.status}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                ⏳ Connecting...
              </p>
            )}
          </div>

          {/* Stack info */}
          <div className="flex flex-wrap gap-2 justify-center">
            {["FastAPI", "React", "SQLite", "Tailwind"].map((tech) => (
              <span
                key={tech}
                className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold"
              >
                {tech}
              </span>
            ))}
          </div>

          <Button className="w-full" size="lg">
            Get Started
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default App;
