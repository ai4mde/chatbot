import { json } from "@remix-run/server-runtime";
import { useLoaderData } from "@remix-run/react";

export async function loader() {
  return json({ message: "Admin test route works!" });
}

export default function AdminTestPage() {
  const { message } = useLoaderData<typeof loader>();
  return <h1>{message}</h1>;
} 