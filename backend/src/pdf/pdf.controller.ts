import {
  Controller,
  Post,
  Body,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import axios from 'axios';
import { ApiResponse } from '../types';

@Controller()
export class PdfController {
  @Post('/view-pdf')
  async viewPdf(@Body() body: { path: string }) {
    if (!body.path?.trim()) {
      throw new HttpException('Missing or empty path', HttpStatus.BAD_REQUEST);
    }

    try {
      const response = await axios.post(
        'http://python-rag-service:8000/api/view-pdf',
        body,
      );
      return response.data as ApiResponse;
    } catch (error: any) {
      throw new HttpException(
        error?.response?.data?.message || 'PDF processing failed',
        error?.response?.status || HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
