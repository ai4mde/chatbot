import React, { useEffect } from "react";
import {
  Outlet,
  useLoaderData,
  Form, // Import Form for delete action
  useActionData, // Import useActionData for feedback
  useNavigation, // Import useNavigation for pending states
  useRevalidator, // Import useRevalidator to refresh data
} from "@remix-run/react";
import { LoaderFunctionArgs, ActionFunctionArgs, MetaFunction, redirect } from "@remix-run/node";
import { json } from "@remix-run/server-runtime";

// TanStack Table imports
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getPaginationRowModel, // For pagination
  Row,
  Header,
  Cell,
  CellContext,
  HeaderGroup,
  HeaderContext,
} from "@tanstack/react-table";

// Shadcn UI component imports
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { Button } from "~/components/ui/button";
import { Checkbox } from "~/components/ui/checkbox"; // For boolean flags
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react"; // For actions button icon
import { toast, useToast } from "~/components/ui/use-toast"; // Import useToast
import { CreateUserDialog } from "~/components/admin/CreateUserDialog"; // Import the new dialog

// TODO: Implement API client/helpers for authenticated fetch
import { authenticator } from "~/services/auth.server"; // To get user/token

// Backend URL (ensure this is configured, e.g., via environment variables)
const CHATBACK_URL = process.env.CHATBACK_URL || 'http://localhost:8000';

// Type for Group data (mirroring backend schema)
type Group = {
  id: number;
  name: string;
  description?: string | null;
};

// User type definition (ensure this matches backend schema fully)
type User = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  group_id: number | null;
  group?: { id: number; name: string } | null; // Make group optional if not always joined
  created_at: string; // Add other fields as needed
  updated_at: string | null;
};

// Define columns for the user table
export const columns: ColumnDef<User>[] = [
  {
    accessorKey: "id",
    header: "ID",
  },
  {
    accessorKey: "username",
    header: "Username",
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "group", // Access nested data
    header: "Group",
    cell: ({ row }: CellContext<User, unknown>) => row.original.group?.name ?? "N/A", // Display group name or N/A
  },
  {
    accessorKey: "is_admin",
    header: "Admin",
    cell: ({ row }: CellContext<User, unknown>) => <Checkbox checked={row.getValue("is_admin")} disabled />, // Display as checkbox
  },
  {
    accessorKey: "is_active",
    header: "Active",
    cell: ({ row }: CellContext<User, unknown>) => <Checkbox checked={row.getValue("is_active")} disabled />,
  },
  {
    id: "actions",
    cell: ({ row }: CellContext<User, unknown>) => {
      const user = row.original;
      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => navigator.clipboard.writeText(user.email)}
            >
              Copy Email
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {/* TODO: Implement Edit action (e.g., open dialog) */}
            <DropdownMenuItem>Edit User</DropdownMenuItem>
            {/* Delete action using a Remix Form */}
            <Form method="post" style={{ display: 'inline' }}>
              <input type="hidden" name="_action" value="deleteUser" />
              <input type="hidden" name="userId" value={user.id} />
              {/* TODO: Add confirmation dialog before submitting */}
              <DropdownMenuItem 
                className="text-destructive focus:text-destructive focus:bg-destructive/10"
                onSelect={(e) => e.preventDefault()} // Prevent menu closing before form submits
              >
                 <button type="submit" className="w-full text-left">
                    Delete User
                 </button>
              </DropdownMenuItem>
            </Form>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];

// Implement fetch function to call backend API with auth
async function fetchUsers(request: Request): Promise<User[]> {
  console.log("Attempting to fetch users from backend...");
  
  // 1. Get the authenticated user and their token
  const userSession = await authenticator.isAuthenticated(request);
  if (!userSession?.access_token) {
    console.error("fetchUsers: No authenticated user session or token found.");
    throw new Error("Authentication required to fetch users."); // Or handle appropriately
  }

  const token = userSession.access_token;
  const backendUrl = `${CHATBACK_URL}/api/v1/admin/users`; // Adjust endpoint if necessary

  try {
    // 2. Make the authenticated API call
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    // 3. Handle the response
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`fetchUsers: Failed to fetch users from backend. Status: ${response.status}, Body: ${errorText}`);
      throw new Error(`Failed to load users (Status: ${response.status}).`);
    }

    const users: User[] = await response.json();
    console.log(`fetchUsers: Successfully fetched ${users.length} users.`);
    return users;

  } catch (error) {
    console.error("fetchUsers: Error during fetch operation:", error);
    // Re-throw the error so the loader can catch it and display an error message
    if (error instanceof Error) {
        throw error;
    } else {
        throw new Error("An unknown error occurred while fetching users.");
    }
  }
}

// Fetch groups function
async function fetchGroups(request: Request): Promise<Group[]> {
  console.log("Attempting to fetch groups from backend...");
  const userSession = await authenticator.isAuthenticated(request);
  if (!userSession?.access_token) {
    throw new Error("Authentication required to fetch groups.");
  }
  const token = userSession.access_token;
  const backendUrl = `${CHATBACK_URL}/api/v1/admin/groups`; // Adjust if necessary
  
  // --- Add explicit logging ---
  console.log(`fetchGroups: Attempting to fetch from URL: ${backendUrl}`);
  // ---------------------------

  try {
    const response = await fetch(backendUrl, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`fetchGroups: Failed. Status: ${response.status}, Body: ${errorText}`);
      throw new Error(`Failed to load groups (Status: ${response.status}).`);
    }
    const groups: Group[] = await response.json();
    console.log(`fetchGroups: Successfully fetched ${groups.length} groups.`);
    return groups;
  } catch (error) {
    console.error("fetchGroups: Error during fetch:", error);
    if (error instanceof Error) throw error;
    throw new Error("An unknown error occurred while fetching groups.");
  }
}

// Update LoaderData type
type LoaderData = {
  users: User[];
  groups: Group[]; // Add groups
  error?: string;
};

// Define a type for the action return data for better type checking
type ActionResponse = 
  | { successMessage: string; formError?: never; error?: never }
  | { formError: string; successMessage?: never; error?: never }
  | { error: string; successMessage?: never; formError?: never }
  | { ok: boolean; formError?: never; successMessage?: never; error?: never } // For simple delete success
  | null; // Can be null if no action was taken or on initial load

export async function loader({ request }: LoaderFunctionArgs): Promise<Response> {
  try {
    // Fetch users and groups in parallel
    const [users, groups] = await Promise.all([
      fetchUsers(request.clone()), // Clone request if using it multiple times
      fetchGroups(request.clone()),
    ]);
    return json<LoaderData>({ users, groups });
  } catch (error) {
    console.error("Failed to load users or groups:", error);
    const message = error instanceof Error ? error.message : "Failed to load data.";
    // Return empty arrays on error, but include error message
    return json<LoaderData>({ users: [], groups: [], error: message }, { status: 500 });
  }
}

// Action function to handle user deletion AND creation
export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const actionType = formData.get("_action");
  const userSession = await authenticator.isAuthenticated(request);

  if (!userSession?.access_token) {
    return json({ error: "Authentication required" }, { status: 401 });
  }
  const token = userSession.access_token;

  // --- Handle Delete User --- 
  if (actionType === "deleteUser") {
    const userId = formData.get("userId");
    if (typeof userId !== "string") {
      return json({ formError: "Invalid User ID for deletion" }, { status: 400 });
    }
    const backendUrl = `${CHATBACK_URL}/api/v1/admin/users/${userId}`;
    try {
      console.log(`Attempting to delete user ID: ${userId}`);
      const response = await fetch(backendUrl, { 
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to delete user" }));
        console.error("Delete failed:", errorData);
        throw new Error(errorData.detail || "Failed to delete user");
      }
      console.log(`User ${userId} deleted successfully.`);
      return json({ successMessage: `User ${userId} deleted successfully.` }); 
    } catch (error) {
      console.error("Failed to delete user:", error);
      const message = error instanceof Error ? error.message : "Unknown error";
      return json({ formError: `Failed to delete user: ${message}` }, { status: 500 });
    }
  }

  // --- Handle Create User --- 
  if (actionType === "createUser") {
    const username = formData.get("username") as string;
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;
    const isAdmin = formData.get("is_admin") === "on"; // Checkbox value is 'on' or null
    const groupIdStr = formData.get("group_id") as string | undefined;
    const groupId = groupIdStr && groupIdStr !== "" ? parseInt(groupIdStr, 10) : null;

    // Basic validation (backend will do more thorough validation)
    if (!username || !email || !password) {
      return json({ formError: "Username, email, and password are required." }, { status: 400 });
    }
    if (groupIdStr && isNaN(groupId as number)) {
        return json({ formError: "Invalid Group ID." }, { status: 400 });
    }

    const backendUrl = `${CHATBACK_URL}/api/v1/admin/users`;
    try {
      console.log("Attempting to create user:", { username, email, isAdmin, groupId });
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          username,
          email,
          password,
          is_admin: isAdmin,
          group_id: groupId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to create user" }));
        console.error("Create user failed:", errorData);
        throw new Error(errorData.detail || "Failed to create user");
      }
      
      const newUser = await response.json();
      console.log("User created successfully:", newUser);
      return json({ successMessage: `User '${username}' created successfully.` });

    } catch (error) {
      console.error("Failed to create user:", error);
      const message = error instanceof Error ? error.message : "Unknown error";
      // Return error message to be displayed in the form/toast
      return json({ formError: `Failed to create user: ${message}` }, { status: 500 });
    }
  }

  // --- Invalid Action --- 
  return json({ formError: "Invalid action" }, { status: 400 });
}

export default function AdminUsersPage() {
  const { users, groups, error } = useLoaderData<LoaderData>();
  // Use the specific type for actionData
  const actionData = useActionData<ActionResponse>(); 
  const navigation = useNavigation();
  const { toast } = useToast();
  const revalidator = useRevalidator();

  const isSubmitting = navigation.state === "submitting";

  // Effect to show toast messages based on actionData
  useEffect(() => {
    // Use optional chaining and type checking
    if (actionData && 'successMessage' in actionData && actionData.successMessage) {
      toast({ title: "Success", description: actionData.successMessage });
      revalidator.revalidate(); // Revalidate data on success
      // TODO: Close the dialog if it's open (needs state management or ref)
      // One way: Pass revalidator state or actionData down to dialog?
    } else if (actionData && 'formError' in actionData && actionData.formError) {
      toast({ variant: "destructive", title: "Error", description: actionData.formError });
    } else if (actionData && 'error' in actionData && actionData.error) { // Handle general error from auth check
       toast({ variant: "destructive", title: "Auth Error", description: actionData.error });
    }
  }, [actionData, toast, revalidator]);

  const table = useReactTable({
    data: users ?? [], // Provide default empty array
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(), // Enable pagination
    initialState: {
        pagination: {
            pageSize: 10, // Default page size
        },
    },
  });

  if (error) {
    return <p className="text-destructive">Error loading page data: {error}</p>;
  }

  return (
    <div className="w-full">
      <div className="flex justify-between items-center py-4">
        <h1 className="text-2xl font-bold">User Management</h1>
        {/* Wrap the Button with the Dialog Trigger */}
        <CreateUserDialog groups={groups ?? []}> 
          <Button disabled={isSubmitting}>
            {isSubmitting && navigation.formData?.get('_action') === 'createUser' 
              ? "Creating..." 
              : "Create User"}
          </Button>
        </CreateUserDialog>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup: HeaderGroup<User>) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header: Header<User, unknown>) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row: Row<User>) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell: Cell<User, unknown>) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {/* Pagination Controls */}
      <div className="flex items-center justify-end space-x-2 py-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          Next
        </Button>
      </div>
      {/* Outlet for potential nested routes */}
      <Outlet /> 
    </div>
  );
} 