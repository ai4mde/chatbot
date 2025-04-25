import { json } from "@remix-run/server-runtime";
import { useLoaderData, useFetcher, useRevalidator, Form } from "@remix-run/react";
import { LoaderFunctionArgs, ActionFunctionArgs, MetaFunction, redirect } from "@remix-run/node";
import { useState, useEffect } from "react";
import { authenticator } from "~/services/auth.server";
import { getSession } from "~/services/session.server";
import { fetchWithAuth } from "~/utils/fetchWithAuth";

// Shadcn UI Imports
import { Button } from "~/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "~/components/ui/card";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { toast } from "sonner";
import { AlertCircle, CheckCircle, Trash2, PlusCircle, Settings } from "lucide-react";

// Define types based on backend schemas
interface QdrantStatus {
  connected: boolean;
  version?: string;
  error?: string;
}

interface QdrantCollectionInfo {
  name: string;
  vectors_count?: number | null;
  points_count?: number | null;
  status?: string | null; 
}

interface LoaderData {
  status: QdrantStatus;
  collections: QdrantCollectionInfo[];
  error?: string; // General loader error
}

export const meta: MetaFunction = () => {
  return [{ title: "Admin - Vector DB Management" }];
};

// Restore Loader function to fetch Qdrant status and collections
export async function loader({ request }: LoaderFunctionArgs) {
  console.log("[Vector DB Loader] Attempting authentication...");
  let user;
  try {
    user = await authenticator.isAuthenticated(request, {
      failureRedirect: "/login",
    });
    console.log("[Vector DB Loader] Authentication successful, user:", user ? user.username : 'No user found but no redirect');
  } catch (error) {
    console.error("[Vector DB Loader] Authentication check failed:", error);
    // Re-throw or handle appropriately - maybe redirect manually?
    // For now, log and let it proceed to check accessToken (which will likely fail)
  }
  
  // TODO: Add check if user is admin here if possible, or handle 403 from API calls
  // if (user && !user.is_admin) { 
  //   console.warn("[Vector DB Loader] User is not admin, redirecting...");
  //   // Redirect non-admins away? Maybe to a specific page or just /
  //   // return redirect("/"); 
  // }

  const session = await getSession(request);
  const accessToken = session.get(authenticator.sessionKey)?.accessToken;
  console.log("[Vector DB Loader] Access Token present:", !!accessToken);

  if (!accessToken) {
    return redirect("/login");
  }

  try {
    console.log("[Vector DB Route] Fetching Qdrant status...");
    const statusPromise = fetchWithAuth(
      `${process.env.CHATBACK_URL}/api/v1/admin/vector-db/status`,
      accessToken
    );
    console.log("[Vector DB Route] Fetching Qdrant collections...");
    const collectionsPromise = fetchWithAuth(
      `${process.env.CHATBACK_URL}/api/v1/admin/vector-db/collections`,
      accessToken
    );

    const [statusRes, collectionsRes] = await Promise.all([
      statusPromise,
      collectionsPromise,
    ]);

    let statusData: QdrantStatus = { connected: false, error: "Failed to fetch status" };
    let collectionsData: QdrantCollectionInfo[] = [];
    let loaderError: string | undefined;

    if (statusRes.ok) {
      statusData = await statusRes.json();
      console.log("[Vector DB Route] Qdrant Status:", statusData);
    } else {
      console.error("[Vector DB Route] Failed to fetch status:", statusRes.status, await statusRes.text());
      statusData.error = `Failed to fetch status: ${statusRes.status}`;
      loaderError = statusData.error; // Set general loader error
    }

    // Fetch collections regardless of status and let the UI handle display logic
    if (collectionsRes.ok) {
      const collectionsPayload = await collectionsRes.json();
      collectionsData = collectionsPayload.collections;
      console.log("[Vector DB Route] Qdrant Collections:", collectionsData);
    } else {
      console.error("[Vector DB Route] Failed to fetch collections:", collectionsRes.status, await collectionsRes.text());
      loaderError = loaderError ? `${loaderError}; Failed to fetch collections: ${collectionsRes.status}` : `Failed to fetch collections: ${collectionsRes.status}`;
    }

    return json<LoaderData>({ status: statusData, collections: collectionsData, error: loaderError });

  } catch (error: any) {
    console.error("[Vector DB Route] Loader error:", error);
    return json<LoaderData>({ 
        status: { connected: false, error: "Network or parsing error occurred" }, 
        collections: [], 
        error: error.message || "An unexpected error occurred during loading."
    }, { status: 500 });
  }
}

// Restore Action function to handle create/delete
export async function action({ request }: ActionFunctionArgs) {
  const user = await authenticator.isAuthenticated(request, {
    failureRedirect: "/login",
  });
  // TODO: Add check if user is admin

  const session = await getSession(request);
  const accessToken = session.get(authenticator.sessionKey)?.accessToken;

  if (!accessToken) {
    return json({ ok: false, error: "Unauthorized" }, { status: 401 });
  }

  const formData = await request.formData();
  const intent = formData.get("intent");
  const collectionName = formData.get("collectionName") as string;

  try {
    let response: Response;
    if (intent === "create") {
      if (!collectionName) {
        return json({ ok: false, error: "Collection name is required for creation." }, { status: 400 });
      }
      console.log(`[Vector DB Action] Attempting to create collection: ${collectionName}`);
      response = await fetchWithAuth(
        `${process.env.CHATBACK_URL}/api/v1/admin/vector-db/collections`,
        accessToken,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: collectionName }),
        }
      );
    } else if (intent === "delete") {
       if (!collectionName) {
        return json({ ok: false, error: "Collection name is required for deletion." }, { status: 400 });
      }
      console.log(`[Vector DB Action] Attempting to delete collection: ${collectionName}`);
      response = await fetchWithAuth(
        `${process.env.CHATBACK_URL}/api/v1/admin/vector-db/collections/${encodeURIComponent(collectionName)}`,
        accessToken,
        { method: "DELETE" }
      );
    } else {
      return json({ ok: false, error: "Invalid intent." }, { status: 400 });
    }

    if (response.ok) {
      console.log(`[Vector DB Action] ${intent} action successful for ${collectionName}`);
      if (response.status === 204) { // Handle DELETE (204 No Content)
         return json({ ok: true, message: `Collection '${collectionName}' deleted successfully.` });
      }
      const data = await response.json();
      return json({ ok: true, message: `Collection '${collectionName}' created successfully.`, data });
    } else {
      const errorData = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
      console.error(`[Vector DB Action] ${intent} action failed for ${collectionName}:`, response.status, errorData);
      return json({ ok: false, error: errorData.detail || `Failed to ${intent} collection. Status: ${response.status}` }, { status: response.status });
    }

  } catch (error: any) {
     console.error(`[Vector DB Action] Action error (${intent}):`, error);
     return json({ ok: false, error: error.message || "An unexpected network or server error occurred." }, { status: 500 });
  }
}

// --- Restore Original Component --- 

export default function AdminVectorDbPage() {
  const { status, collections, error: loaderError } = useLoaderData<LoaderData>();
  const createFetcher = useFetcher<any>();
  const deleteFetcher = useFetcher<any>();
  const revalidator = useRevalidator();
  const [newCollectionName, setNewCollectionName] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  // Handle create submission
  const handleCreateSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newCollectionName.trim()) {
        toast.error("Collection name cannot be empty.");
        return;
    }
    createFetcher.submit(
      { intent: "create", collectionName: newCollectionName.trim() },
      { method: "post" }
    );
    setNewCollectionName(""); // Clear input after submission attempt
  };

  // Handle delete confirmation
  const handleDelete = (collectionName: string) => {
      // Use sonner or a custom dialog for better confirmation UX later
      if (window.confirm(`Are you sure you want to delete the collection "${collectionName}"? This action cannot be undone.`)) {
          deleteFetcher.submit(
              { intent: "delete", collectionName },
              { method: "post" }
          );
      }
  };

  // Display toasts based on fetcher results
  useEffect(() => {
      if (createFetcher.state === "idle" && createFetcher.data) {
          if (createFetcher.data.ok) {
              toast.success(createFetcher.data.message || "Collection created!");
              setIsCreateDialogOpen(false); // Close dialog on success
              revalidator.revalidate(); // Reload data
          } else {
              toast.error(createFetcher.data.error || "Failed to create collection.");
          }
          // Potential issue: Fetcher data might persist across navigations.
          // Consider clearing fetcher.data if it causes duplicate toasts.
      }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createFetcher.state, createFetcher.data, revalidator]);

  useEffect(() => {
       if (deleteFetcher.state === "idle" && deleteFetcher.data) {
          if (deleteFetcher.data.ok) {
              toast.success(deleteFetcher.data.message || "Collection deleted!");
              revalidator.revalidate(); // Reload data
          } else {
              toast.error(deleteFetcher.data.error || "Failed to delete collection.");
          }
      }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deleteFetcher.state, deleteFetcher.data, revalidator]);

  // Display initial loader error toast
  useEffect(() => {
      if (loaderError) {
          toast.error(`Failed to load data: ${loaderError}`);
      }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaderError]); // Run only when loaderError changes

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Vector Database Management</h1>
      
      {/* Connection Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" /> Qdrant Connection Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          {status.connected ? (
            <p className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" /> Connected
              {/* {status.version && <span> (Version: {status.version})</span>} */}
            </p>
          ) : (
            <p className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-5 w-5" /> Disconnected
              {status.error && <span className="text-sm text-muted-foreground">- {status.error}</span>}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Collections Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Collections</CardTitle>
            <CardDescription>Manage Qdrant vector collections.</CardDescription>
          </div>
          {/* Create Collection Dialog Trigger */}
           <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button disabled={!status.connected || createFetcher.state !== 'idle'}>
                <PlusCircle className="mr-2 h-4 w-4" /> Create Collection
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <createFetcher.Form method="post" onSubmit={handleCreateSubmit}>
                <DialogHeader>
                  <DialogTitle>Create New Collection</DialogTitle>
                  <DialogDescription>
Enter a unique name for the new vector collection.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="collectionName" className="text-right">
                      Name
                    </Label>
                    <Input
                      id="collectionName"
                      name="collectionName"
                      value={newCollectionName}
                      onChange={(e) => setNewCollectionName(e.target.value)}
                      className="col-span-3"
                      required
                      disabled={createFetcher.state !== 'idle'}
                    />
                  </div>
                </div>
                 {/* Hidden intent field */}
                <input type="hidden" name="intent" value="create" />
                <DialogFooter>
                   <DialogClose asChild>
                      <Button type="button" variant="outline" disabled={createFetcher.state !== 'idle'}>
                        Cancel
                      </Button>
                   </DialogClose>
                  <Button type="submit" disabled={!newCollectionName.trim() || createFetcher.state !== 'idle'}>
                    {createFetcher.state === 'submitting' ? "Creating..." : "Create Collection"}
                  </Button>
                </DialogFooter>
              </createFetcher.Form>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          <Table>
            <TableCaption>A list of your Qdrant collections.</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Points/Vectors</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {collections.length > 0 ? (
                collections.map((collection) => (
                  <TableRow key={collection.name}>
                    <TableCell className="font-medium">{collection.name}</TableCell>
                    <TableCell>{collection.status || "N/A"}</TableCell>
                    <TableCell>{collection.points_count ?? "N/A"}</TableCell>
                    <TableCell className="text-right">
                       <Button 
                          variant="destructive" 
                          size="sm"
                          onClick={() => handleDelete(collection.name)}
                          disabled={!status.connected || deleteFetcher.state !== 'idle' || collection.name === 'chat_messages'} // Disable delete for main chat collection
                          title={collection.name === 'chat_messages' ? "Cannot delete primary chat collection" : "Delete collection"}
                        >
                          {deleteFetcher.state === 'submitting' && deleteFetcher.formData?.get('collectionName') === collection.name ? 
                           "Deleting..." : 
                           <Trash2 className="h-4 w-4" />
                          }
                       </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="text-center">
                    {status.connected ? "No collections found." : "Cannot fetch collections (Qdrant disconnected)."}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
} 