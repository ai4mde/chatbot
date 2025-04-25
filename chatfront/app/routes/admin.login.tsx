import React from "react";
import { Form, useActionData, useNavigation } from "@remix-run/react";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node"; // or cloudflare/deno
import { redirect } from "@remix-run/node"; // Remove json
import { json } from "@remix-run/server-runtime"; // Add json

import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";

// Import the authenticator
import { authenticator } from "~/services/auth.server";
// Assuming sessionStorage is exported from session.server.ts
import { sessionStorage } from "~/services/session.server"; 

// Loader function to redirect if already logged in as admin
export async function loader({ request }: LoaderFunctionArgs) {
  // Pass the request object directly
  const user = await authenticator.isAuthenticated(request);
  if (user && user.is_admin) {
    return redirect("/admin");
  }
  // If not admin or not logged in, destroy any existing session and show login
  const session = await sessionStorage.getSession(request.headers.get("Cookie"));
  return json({}, {
    headers: {
      // Use destroySession to clear the session cookie
      "Set-Cookie": await sessionStorage.destroySession(session)
    }
  });
}

// Action function now uses the authenticator
export async function action({ request }: ActionFunctionArgs) {
  // Use the 'admin-form' strategy
  try {
    // `authenticate` will redirect on success or throw on failure by default
    // if failureRedirect is set. If not, it returns the user on success.
    // We might want failure to return data to the form instead.
    return await authenticator.authenticate("admin-form", request, {
      successRedirect: "/admin",
      // We handle failure by returning the error message to the form
      // To do this, the strategy needs to throw an error on failure, 
      // which we catch here.
      // Alternatively, configure strategy to return user/null and check here.
    });
  } catch (error) {
    // Handle specific error messages thrown by the strategy
    if (error instanceof Error) {
        // Check for specific error messages if needed
        if (error.message === 'User does not have admin privileges.') {
            return json({ error: "Admin privileges required." }, { status: 403 });
        }
        // Return generic credentials error
        return json({ error: "Invalid username or password." }, { status: 401 });
    }
    // Handle unexpected errors
    console.error("Admin Login Action Error:", error);
    return json({ error: "An unexpected error occurred." }, { status: 500 });
  }
}

export default function AdminLoginPage() {
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const isSubmitting = navigation.state === "submitting";

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40">
      <Card className="mx-auto max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Admin Login</CardTitle>
          <CardDescription>
            Enter your credentials to access the admin panel
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Use Remix Form, method POST is default */}
          <Form method="post" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input 
                id="username" 
                name="username" 
                type="text" 
                placeholder="admin" 
                required 
                aria-invalid={Boolean(actionData?.error)}
                aria-errormessage={actionData?.error ? "error-message" : undefined}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input 
                id="password" 
                name="password" 
                type="password" 
                required 
                aria-invalid={Boolean(actionData?.error)}
                aria-errormessage={actionData?.error ? "error-message" : undefined}
              />
            </div>
            {/* Display error message */}
            {actionData?.error && (
              <p id="error-message" className="text-sm font-medium text-destructive">
                {actionData.error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : "Login"}
            </Button>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
} 