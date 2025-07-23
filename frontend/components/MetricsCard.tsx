'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface Props {
  title: string;
  value: string | number;
}

export default function MetricsCard({ title, value }: Props) {
  return (
    <Card className="w-full">
      <CardHeader className="pb-2 text-sm font-medium text-muted-foreground">
        {title}
      </CardHeader>
      <CardContent className="text-2xl font-bold">{value}</CardContent>
    </Card>
  );
} 