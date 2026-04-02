import { IsString, IsNumber } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';

export class ChatDto {
  @ApiProperty()
  @IsNumber()
  @Type(() => String)
  documentId: string;

  @ApiProperty()
  @IsString()
  question: string;
}
