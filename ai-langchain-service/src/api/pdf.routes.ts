import { Router,  RequestHandler  } from 'express';
import { handleViewPdf } from '../app/pdf/pdfViewer';

const router = Router();

router.post('/view-pdf', handleViewPdf as RequestHandler);

export default router;
