import {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
  Button,
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  Label,
  Input,
} from '../../components/ui';
import Header from './sections/Header'
import Footer from './sections/Footer'
import Content from './sections/Content'

export default function LandingPage() {




  return (
    <>
      <Header />
			<Content />
			<Footer />
    </>
  );
}



{/* <div style={{'alignItems': 'center', 'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}}>
        <Button variant="link">Это кнопка</Button>
        <Button variant="destructive">Это кнопка</Button>
        <Button variant="ghost">Это кнопка</Button>
        <Button variant="outline">Это кнопка</Button>
        <Button variant="primary">Это кнопка</Button>
        <Button variant="secondary">Это кнопка</Button>
      </div> */}

{
  /* <Card style={{ width: "100%" }}>
      <CardHeader>
        <CardTitle>Login to your account</CardTitle>
        <CardDescription>
          Enter your email below to login to your account
        </CardDescription>
        <CardAction>
          <Button variant="link">Sign Up</Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        <form>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div style={{ display: "grid", gap: "8px" }}>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                required
              />
            </div>
            <div style={{ display: "grid", gap: "8px" }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <Label htmlFor="password">Password</Label>
                <a
                  href="#"
                  style={{
                    marginInlineStart: "auto",
                    display: "inline-block",
                    fontSize: "14px",
                  }}>
                  Forgot your password?
                </a>
              </div>
              <Input id="password" type="password" required />
            </div>
          </div>
        </form>
      </CardContent>
      <CardFooter style={{ flexDirection: "column", gap: "8px" }}>
        <Button type="submit" style={{ width: "100%" }}>
          Login
        </Button>
        <Button variant="outline" style={{ width: "100%" }}>
          Login with Google
        </Button>
      </CardFooter>
    </Card>
		<Label>Привет</Label>
		<Input type='file' />
      <Button> Кнопка </Button>
      <Pagination>
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious href="#" />
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#">1</PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#" isActive>
              2
            </PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#">3</PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationEllipsis />
          </PaginationItem>
          <PaginationItem>
            <PaginationNext href="#" />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
      <Carousel style={{ width: '500px', margin: '0 auto' }}>
        <CarouselContent>
          {Array.from({ length: 5 }).map((_, index) => (
            <CarouselItem key={index}>
              <div style={{ padding: '4px' }}>
                <Card>
                  <CardContent
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '24px',
                      aspectRatio: 1,
                    }}
                  >
                    <span style={{ fontSize: '36px', fontWeight: '600' }}>
                      {index + 1}
                    </span>
                  </CardContent>
                </Card>
              </div>
            </CarouselItem>
          ))}
        </CarouselContent>
        <CarouselPrevious />
        <CarouselNext />
      </Carousel>
      ; */
}
