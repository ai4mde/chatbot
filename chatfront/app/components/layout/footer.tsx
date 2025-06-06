import * as React from 'react';
import { Link } from '@remix-run/react';

export function Footer() {
  return (
    <footer className='border-t'>
      <div className='container flex flex-col items-center py-8 gap-4'>
        <nav className='flex gap-4'>
          <Link to='/privacy' className='text-sm underline underline-offset-4'>
            Privacy
          </Link>
          <Link to='/terms' className='text-sm underline underline-offset-4'>
            Terms
          </Link>
          <Link to='/contact' className='text-sm underline underline-offset-4'>
            Contact
          </Link>
        </nav>
        <p className='text-center text-sm leading-loose'>
          Built for{' '}
          <a
            href='https://www.universiteitleiden.nl/en/education/masters/master-talks/programme-videos/ict-in-business-and-the-public-sector/ict-in-business-and-the-public-sector'
            target='_blank'
            rel='noreferrer'
            className='font-medium underline underline-offset-4'
          >
            Leiden University
          </a>
          . The source code is available on{' '}
          <a
            href='https://github.com/ai4mde/chatbot'
            target='_blank'
            rel='noreferrer'
            className='font-medium underline underline-offset-4'
          >
            GitHub
          </a>
          .
        </p>
      </div>
    </footer>
  );
} 