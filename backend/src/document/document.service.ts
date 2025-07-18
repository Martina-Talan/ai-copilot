import {
  Injectable,
  NotFoundException,
  InternalServerErrorException,
  Logger,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Document as DocumentEntity } from './entity/document.entity';
import { User } from '../user/entity/user.entity';

@Injectable()
export class DocumentService {
  private readonly logger = new Logger(DocumentService.name);

  constructor(
    @InjectRepository(DocumentEntity)
    private documentRepo: Repository<DocumentEntity>,
    @InjectRepository(User)
    private userRepo: Repository<User>,
  ) {}

  async getDocumentsByUserId(userId: number): Promise<DocumentEntity[]> {
    try {
      return await this.documentRepo.find({
        where: { user: { id: userId } },
        relations: ['user'],
      });
    } catch (error) {
      this.logger.error(
        `Failed to get documents for userId ${userId}`,
        error.stack,
      );
      throw new InternalServerErrorException('Could not fetch documents');
    }
  }

  async deleteDocument(id: number, userId: number): Promise<void> {
    try {
      const doc = await this.documentRepo.findOne({
        where: { id, user: { id: userId } },
        relations: ['user'],
      });

      if (!doc) {
        throw new NotFoundException('Document not found');
      }

      await this.documentRepo.remove(doc);
    } catch (error) {
      this.logger.error(
        `Failed to delete document with id ${id} for user ${userId}`,
        error.stack,
      );
      throw error instanceof NotFoundException
        ? error
        : new InternalServerErrorException('Could not delete document');
    }
  }

  async saveFileMetadata(
    filename: string,
    path: string,
    userId: number,
  ): Promise<DocumentEntity> {
    const user = await this.userRepo.findOne({ where: { id: userId } });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    const doc = this.documentRepo.create({ filename, path, user });

    try {
      return await this.documentRepo.save(doc);
    } catch (error) {
      this.logger.error(
        `Failed to save document metadata for user ${userId}`,
        error.stack,
      );
      throw new InternalServerErrorException(
        'Could not save document metadata',
      );
    }
  }
}
