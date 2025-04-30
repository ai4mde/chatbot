import React, { useEffect } from "react";
import { 
  Outlet, 
  useLoaderData, 
  Form, // Import Form for delete action
  useActionData,
  useNavigation,
  useRevalidator,
} from "@remix-run/react";
import { LoaderFunctionArgs, ActionFunctionArgs, MetaFunction, redirect } from "@remix-run/node";
import { json } from "@remix-run/server-runtime";
import { authenticator } from "~/services/auth.server";

// TanStack Table imports
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getPaginationRowModel, 
  Row,
  Header,
  Cell,
  CellContext,
  HeaderGroup,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import { useToast } from "~/components/ui/use-toast";
import { CreateGroupDialog } from "~/components/admin/CreateGroupDialog";

// Backend URL
const CHATBACK_URL = process.env.CHATBACK_URL || 'http://localhost:8000';

// Type for Group data
type Group = {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string | null;
};

// Define columns for the group table
export const columns: ColumnDef<Group>[] = [
  {
    accessorKey: "id",
    header: "ID",
  },
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }: CellContext<Group, unknown>) => row.getValue("description") || <span className="text-muted-foreground">N/A</span>,
  },
   {
    accessorKey: "created_at",
    header: "Created At",
    cell: ({ row }: CellContext<Group, unknown>) => {
      const date = new Date(row.getValue("created_at"));
      return date.toLocaleDateString(); // Format date nicely
    },
  },
  {
    id: "actions",
    cell: ({ row }: CellContext<Group, unknown>) => {
      const group = row.original;
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
            {/* TODO: Implement Edit action */} 
            <DropdownMenuItem>Edit Group</DropdownMenuItem>
            <DropdownMenuSeparator />
            {/* Delete action using a Remix Form */}
            <Form method="post" style={{ display: 'inline' }}>
              <input type="hidden" name="_action" value="deleteGroup" />
              <input type="hidden" name="groupId" value={group.id} />
              {/* TODO: Add confirmation dialog */}
              <DropdownMenuItem 
                className="text-destructive focus:text-destructive focus:bg-destructive/10"
                onSelect={(e) => e.preventDefault()} 
              >
                 <button type="submit" className="w-full text-left">
                    Delete Group
                 </button>
              </DropdownMenuItem>
            </Form>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];

// Fetch groups function (similar to the one in users route)
async function fetchGroups(request: Request): Promise<Group[]> {
  console.log("[Groups Route] Attempting to fetch groups from backend...");
  const userSession = await authenticator.isAuthenticated(request);
  if (!userSession?.access_token) {
    throw new Error("Authentication required to fetch groups.");
  }
  const token = userSession.access_token;
  const backendUrl = `${CHATBACK_URL}/api/v1/admin/groups`; 

  try {
    const response = await fetch(backendUrl, {
      headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' },
    });
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Groups Route] Failed to fetch groups. Status: ${response.status}, Body: ${errorText}`);
      throw new Error(`Failed to load groups (Status: ${response.status}).`);
    }
    const groups: Group[] = await response.json();
    console.log(`[Groups Route] Successfully fetched ${groups.length} groups.`);
    return groups;
  } catch (error) {
    console.error("[Groups Route] Error during fetch:", error);
    if (error instanceof Error) throw error;
    throw new Error("An unknown error occurred while fetching groups.");
  }
}

// LoaderData type
type LoaderData = {
  groups: Group[];
  error?: string;
};

// Loader function
export async function loader({ request }: LoaderFunctionArgs): Promise<Response> {
  try {
    const groups = await fetchGroups(request);
    return json<LoaderData>({ groups });
  } catch (error) {
    console.error("[Groups Route] Failed to load groups:", error);
    const message = error instanceof Error ? error.message : "Failed to load group data.";
    return json<LoaderData>({ groups: [], error: message }, { status: 500 });
  }
}

// Define a type for the action response (similar to admin.users)
type ActionResponse = 
  | { successMessage: string; formError?: never; error?: never }
  | { formError: string; successMessage?: never; error?: never }
  | { error: string; successMessage?: never; formError?: never }
  | null;

// Action function to handle group deletion AND creation
export async function action({ request }: ActionFunctionArgs): Promise<Response> {
  const formData = await request.formData();
  const actionType = formData.get("_action");
  const userSession = await authenticator.isAuthenticated(request);

  // Auth Check (add admin check too if necessary, depending on backend requirement)
  if (!userSession?.access_token) {
    return json({ error: "Authentication required" }, { status: 401 });
  }
  // Add admin check if needed:
  // if (!userSession.is_admin) {
  //   return json({ error: "Admin privileges required" }, { status: 403 });
  // }
  const token = userSession.access_token;

  // --- Handle Delete Group --- 
  if (actionType === "deleteGroup") {
    const groupId = formData.get("groupId");
    if (typeof groupId !== "string") {
      return json({ formError: "Invalid Group ID" }, { status: 400 });
    }
    const backendUrl = `${CHATBACK_URL}/api/v1/admin/groups/${groupId}`;
    try {
      console.log(`Attempting to delete group ID: ${groupId}`);
      const response = await fetch(backendUrl, { 
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to delete group" }));
        console.error("Delete group failed:", errorData);
        throw new Error(errorData.detail || "Failed to delete group");
      }
      console.log(`Group ${groupId} deleted successfully.`);
      return json({ successMessage: `Group ${groupId} deleted successfully.` });
    } catch (error) {
      console.error("Failed to delete group:", error);
      const message = error instanceof Error ? error.message : "Unknown error";
      return json({ formError: `Failed to delete group: ${message}` }, { status: 500 });
    }
  }

  // --- Handle Create Group --- 
  if (actionType === "createGroup") {
    const name = formData.get("name") as string;
    const description = formData.get("description") as string | undefined;

    // Basic validation (more can be added, zod schema used client-side)
    if (!name) {
      return json({ formError: "Group name is required." }, { status: 400 });
    }

    const backendUrl = `${CHATBACK_URL}/api/v1/admin/groups`;
    try {
      console.log("Attempting to create group:", { name, description });
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          name,
          description: description || null, // Send null if empty
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to create group" }));
        console.error("Create group failed:", errorData);
        // Try to provide a more specific error if possible
        const detail = errorData?.detail;
        let errorMessage = "Failed to create group";
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // Handle validation errors like FastAPI returns
          errorMessage = detail.map((err: any) => `${err.loc?.join(' -> ') ?? 'field'}: ${err.msg}`).join(", ");
        }
        throw new Error(errorMessage);
      }
      
      const newGroup = await response.json();
      console.log("Group created successfully:", newGroup);
      return json({ successMessage: `Group '${name}' created successfully.` });

    } catch (error) {
      console.error("Failed to create group:", error);
      const message = error instanceof Error ? error.message : "Unknown error";
      // Return error message to be displayed in the form/toast
      return json({ formError: `Failed to create group: ${message}` }, { status: 500 });
    }
  }

  // --- Invalid Action --- 
  return json({ formError: "Invalid action" }, { status: 400 });
}

// Default component for the groups route
export default function AdminGroupsPage() {
  const loaderData = useLoaderData<typeof loader>();
  const actionData = useActionData<ActionResponse>();
  const navigation = useNavigation();
  const { toast } = useToast();
  const revalidator = useRevalidator();

  useEffect(() => {
    if (actionData && 'successMessage' in actionData && actionData.successMessage) {
      toast({ title: "Success", description: actionData.successMessage });
      revalidator.revalidate();
    } else if (actionData && 'formError' in actionData && actionData.formError) {
      toast({ title: "Form Error", description: actionData.formError, variant: "destructive" });
    } else if (actionData && 'error' in actionData && actionData.error) {
      toast({ title: "Error", description: actionData.error, variant: "destructive" });
    }
  }, [actionData, toast, revalidator]);

  const table = useReactTable({
    data: loaderData.groups ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
        pagination: { pageSize: 10 },
    },
  });

  if (loaderData.error) {
    return <p className="text-destructive">Error loading groups: {loaderData.error}</p>;
  }

  const groups = loaderData.groups ?? [];

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Group Management</h1>
        <CreateGroupDialog>
          <Button>Create Group</Button>
        </CreateGroupDialog>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup: HeaderGroup<Group>) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header: Header<Group, unknown>) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row: Row<Group>) => (
                <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                  {row.getVisibleCells().map((cell: Cell<Group, unknown>) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
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
      <Outlet /> 
    </div>
  );
} 