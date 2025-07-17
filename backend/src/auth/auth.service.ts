import {
  BadRequestException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../user/entity/user.entity';

@Injectable()
export class AuthService {
  constructor(
    private readonly jwtService: JwtService,
    @InjectRepository(User)
    private usersRepo: Repository<User>,
  ) {}

  async register(email: string, password: string) {
    const existing = await this.usersRepo.findOne({ where: { email } });
    if (existing) throw new UnauthorizedException('Email already in use');

    if (!password) {
      throw new BadRequestException('Password is required');
    }

    const hash = await bcrypt.hash(password, 10);
    const user: Partial<User> = {
      email,
      password: hash,
    };
    const newUser = this.usersRepo.create(user);
    const savedUser = await this.usersRepo.save(newUser);

    return {
      message: 'User successfully registered',
      user: { id: savedUser.id, email: savedUser.email },
    };
  }
  async login(email: string, password: string) {
    const user = await this.usersRepo.findOne({ where: { email } });
    if (!user) throw new UnauthorizedException('Invalid credentials');

    const valid = await bcrypt.compare(password, user.password);
    if (!valid) throw new UnauthorizedException('Invalid credentials');

    const payload = { sub: user.id, email: user.email };
    const token = this.jwtService.sign(payload);

    return { access_token: token };
  }
}
