import { ApiProperty } from '@nestjs/swagger';
import { Entity, PrimaryGeneratedColumn, Column } from 'typeorm';

@Entity()
export class User {
  @ApiProperty()
  @PrimaryGeneratedColumn()
  id!: number;

  @ApiProperty()
  @Column({ unique: true })
  email!: string;

  @ApiProperty()
  @Column()
  password!: string;
}
