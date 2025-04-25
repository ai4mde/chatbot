import React from "react";
import { Link, NavLink, Outlet, useLoaderData, Form } from "@remix-run/react";
import { cn } from "~/lib/utils"; // Assuming utils file for clsx/tailwind-merge
import { Button } from "~/components/ui/button"; // Assuming Button is installed
import {
  LayoutDashboard,
  Users,
  Group,
  Database,
  Settings, // Added for potential settings page
  LogOut,   // Added for logout
} from "lucide-react";
import type { LoaderFunctionArgs } from "@remix-run/node"; // or cloudflare/deno
import { json } from "@remix-run/node"; // or cloudflare/deno

// Import the authenticator
import { authenticator } from "~/services/auth.server";

// Loader to protect the route
export async function loader({ request }: LoaderFunctionArgs) {
  const user = await authenticator.isAuthenticated(request, {
    // If user is not authenticated, redirect to login
    failureRedirect: "/admin/login",
  });

  // If user is authenticated but NOT an admin, redirect or throw error
  if (!user.is_admin) {
    // You could redirect to a general access denied page or back to home
    // For simplicity, we'll throw a 403 Forbidden error
    // Or redirect to the standard login? throw redirect("/login"); 
    throw json({ message: "Admin access required" }, { status: 403 });
  }

  // If user is authenticated and an admin, return user data
  return json({ user });
}

// You might want to define your nav items in a config array
const navItems = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/groups", label: "Groups", icon: Group },
  { href: "/admin/vector-db", label: "Vector DB", icon: Database },
  // { href: "/admin/settings", label: "Settings", icon: Settings },
];

export default function AdminLayout() {
  // Optionally use loader data if needed in the layout
  // const { user } = useLoaderData<typeof loader>();

  return (
    <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
      {/* Sidebar */}
      <div className="hidden border-r bg-muted/40 md:block">
        <div className="flex h-full max-h-screen flex-col gap-2">
          <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
            <Link to="/admin" className="flex items-center gap-2 font-semibold">
              {/* <Package2 className="h-6 w-6" /> Maybe add a logo */}
              <span className="">Admin Panel</span>
            </Link>
            {/* Add Bell icon for notifications? */}
          </div>
          <div className="flex-1">
            <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
              {navItems.map((item) => (
                <NavLink
                  key={item.href}
                  to={item.href}
                  end // Use 'end' prop for the dashboard link to avoid matching nested routes
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary",
                      isActive && "bg-muted text-primary"
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="mt-auto p-4 border-t">
            <Form action="/logout" method="post">
              <Button type="submit" size="sm" variant="ghost" className="w-full justify-start">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </Form>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col">
        {/* Add a mobile header if needed */}
        {/* <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6 md:hidden">
          Mobile Header Content (e.g., Menu button)
        </header> */}
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          {/* The Outlet renders the matched child route component */}
          <Outlet />
        </main>
      </div>
    </div>
  );
} 