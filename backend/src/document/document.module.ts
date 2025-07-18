import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Document } from './entity/document.entity';
import { DocumentController } from './document.controller';
import { DocumentService } from './document.service';
import { User } from '../user/entity/user.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Document, User])],
  providers: [DocumentService],
  controllers: [DocumentController],
})
export class DocumentModule {}
