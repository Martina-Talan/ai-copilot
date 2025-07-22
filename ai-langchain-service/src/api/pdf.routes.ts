import { Router } from 'express';
import { handleViewPdf } from '../app/pdf/pdfViewer';

const router = Router();

router.post('/view-pdf', handleViewPdf);

export default router;
