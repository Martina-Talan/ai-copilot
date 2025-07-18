import { User } from '../../user/entity/user.entity';
import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  ManyToOne,
} from 'typeorm';

@Entity()
export class Document {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  filename: string;

  @Column()
  path: string;

  @CreateDateColumn()
  uploadedAt: Date;

  @ManyToOne(() => User, (user) => user.documents)
  user: User;
}
