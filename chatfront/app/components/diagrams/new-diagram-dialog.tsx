import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Box, Activity, Users, ArrowDownUp } from 'lucide-react';

interface NewDiagramDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectType: (type: 'class' | 'activity' | 'useCase' | 'sequence') => void;
}

export function NewDiagramDialog({
  open,
  onOpenChange,
  onSelectType,
}: NewDiagramDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Select Diagram Type</DialogTitle>
        </DialogHeader>
        <div className='grid grid-cols-2 gap-4 p-4'>
          <Button
            variant='outline'
            size='lg'
            className='p-8 h-auto flex flex-col items-center gap-4 border-2'
            onClick={() => onSelectType('class')}
          >
            <Box className='h-12 w-12' />
            <div>
              <h3 className='text-lg font-semibold mb-2'>Class Diagram</h3>
            </div>
          </Button>

          <Button
            variant='outline'
            size='lg'
            className='p-8 h-auto flex flex-col items-center gap-4 border-2'
            onClick={() => onSelectType('activity')}
          >
            <Activity className='h-12 w-12' />
            <div>
              <h3 className='text-lg font-semibold mb-2'>Activity Diagram</h3>
            </div>
          </Button>

          <Button
            variant='outline'
            size='lg'
            className='p-8 h-auto flex flex-col items-center gap-4 border-2'
            onClick={() => onSelectType('useCase')}
          >
            <Users className='h-12 w-12' />
            <div>
              <h3 className='text-lg font-semibold mb-2'>Use Case Diagram</h3>
            </div>
          </Button>

          <Button
            variant='outline'
            size='lg'
            className='p-8 h-auto flex flex-col items-center gap-4 border-2'
            onClick={() => onSelectType('sequence')}
          >
            <ArrowDownUp className='h-12 w-12' />
            <div>
              <h3 className='text-lg font-semibold mb-2'>Sequence Diagram</h3>
            </div>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
} 