import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea"; // Use Textarea for description
import { Label } from "~/components/ui/label";
import { useToast } from "~/components/ui/use-toast";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "~/components/ui/form";

// Zod schema for validation
const groupFormSchema = z.object({
  name: z.string().min(1, "Group name is required."),
  description: z.string().optional(), // Description is optional
});

type GroupFormData = z.infer<typeof groupFormSchema>;

interface CreateGroupDialogProps {
  children: React.ReactNode; // To wrap the trigger button
  // Add onSuccess/onClose callbacks if external state management is needed later
}

export function CreateGroupDialog({ children }: CreateGroupDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { toast } = useToast();
  // We might need useRevalidator here later if submission feedback requires page reload

  const form = useForm<GroupFormData>({
    resolver: zodResolver(groupFormSchema),
    defaultValues: {
      name: "",
      description: "",
    },
  });

  // We will rely on the Remix Form to handle the actual submission and feedback loop
  // defined in the admin.groups.tsx action function.

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Group</DialogTitle>
          <DialogDescription>
            Fill in the details for the new group. Click create when you're done.
          </DialogDescription>
        </DialogHeader>
        {/* Use Remix Form for submission to the action */}
        <Form {...form}>
          {/* 
            The onSubmit={form.handleSubmit(...)} is primarily for client-side validation.
            The actual POST request is handled by the <form method="post"> attribute.
            If validation passes client-side, react-hook-form allows the default form submission.
          */}
          <form 
            method="post" 
            action="/admin/groups" // Ensure this points to the correct route action
            onSubmit={form.handleSubmit(() => {
                // Intentionally empty: Let Remix handle the submission after validation.
                // We could potentially call setIsOpen(false) here optimistically,
                // but it's safer to rely on the action feedback (useEffect in parent)
                // to close the dialog on success.
            })} 
            className="space-y-4"
          >
            {/* Add hidden input for the action type */}
            <input type="hidden" name="_action" value="createGroup" />

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Group Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter group name" {...field} />
                  </FormControl>
                  <FormMessage /> 
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Enter group description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
              {/* Disable button during form submission */}
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Creating..." : "Create Group"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
} 