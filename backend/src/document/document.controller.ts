import {
  Controller,
  Get,
  Post,
  UploadedFiles,
  UseGuards,
  UseInterceptors,
  Request,
  Delete,
  Param,
  Req,
  Logger,
  InternalServerErrorException,
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import { DocumentService } from './document.service';
import { ApiBearerAuth, ApiBody, ApiConsumes, ApiTags } from '@nestjs/swagger';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

@ApiTags('documents')
@ApiBearerAuth()
@Controller('documents')
export class DocumentController {
  private readonly logger = new Logger(DocumentController.name);

  constructor(private readonly documentService: DocumentService) {}

  @Post('upload')
  @UseInterceptors(
    FilesInterceptor('files', 10, {
      storage: diskStorage({
        destination: './uploads',
        filename: (req, file, cb) => {
          cb(null, file.originalname);
        },
      }),
      fileFilter: (req, file, cb) => {
        const allowedTypes = [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'text/plain',
        ];
        if (!allowedTypes.includes(file.mimetype)) {
          return cb(
            new Error('Only PDF, DOCX, and TXT files are allowed'),
            false,
          );
        }
        cb(null, true);
      },
    }),
  )
  @ApiConsumes('multipart/form-data')
  @ApiBody({
    schema: {
      type: 'object',
      properties: {
        files: {
          type: 'array',
          items: {
            type: 'string',
            format: 'binary',
          },
        },
      },
    },
  })
  @UseGuards(JwtAuthGuard)
  @Post('upload-multiple')
  async uploadFiles(
    @UploadedFiles() files: Express.Multer.File[],
    @Request() req,
  ) {
    const userId = req.user.id;
    try {
      const results = await Promise.all(
        files.map((file) =>
          this.documentService.saveFileMetadata(
            file.filename,
            file.path,
            userId,
          ),
        ),
      );
      return results;
    } catch (error) {
      this.logger.error(
        `Error uploading files for user ${userId}`,
        error.stack,
      );
      throw new InternalServerErrorException('File upload failed');
    }
  }

  @UseGuards(JwtAuthGuard)
  @Get()
  async getUserDocuments(@Request() req): Promise<any> {
    const userId = req.user.id;
    try {
      const docs = await this.documentService.getDocumentsByUserId(userId);
      this.logger.log(`Fetched ${docs.length} documents for user ${userId}`);
      return docs;
    } catch (error) {
      this.logger.error(
        `Error fetching documents for user ${userId}`,
        error.stack,
      );
      throw new InternalServerErrorException('Could not retrieve documents');
    }
  }

  @UseGuards(JwtAuthGuard)
  @Delete(':id')
  async deleteDocument(@Param('id') id: string, @Req() req: any) {
    const userId = req.user.id;
    try {
      await this.documentService.deleteDocument(Number(id), userId);
      return { message: 'Document deleted successfully' };
    } catch (error) {
      this.logger.error(
        `Failed to delete document ${id} for user ${userId}`,
        error.stack,
      );
      throw new InternalServerErrorException('Could not delete document');
    }
  }
}
