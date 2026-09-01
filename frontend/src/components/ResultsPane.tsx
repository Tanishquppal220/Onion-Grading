import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function ResultsPane({ data }: { data: any }) {
    const imageUrl = `http://localhost:8000/uploads/${data.annotated_image_filename}`;
    
    return (
        <Card className="w-full h-full border-primary/20 shadow-lg shadow-primary/5">
            <CardHeader className="bg-muted/30 pb-4">
                <CardTitle className="text-lg">Grading Results</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                <div className="overflow-hidden rounded-md border border-border shadow-sm">
                    <img src={imageUrl} alt="Annotated Output" className="w-full max-h-80 object-contain bg-muted/20" />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-3">
                        <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">Quality</h3>
                        <ul className="space-y-2 text-sm">
                            <li className="flex justify-between items-center"><span className="text-green-600 font-medium">Healthy Grade A</span> <span className="font-bold text-foreground">{data.onion}</span></li>
                            <li className="flex justify-between items-center"><span className="text-red-500 font-medium">Rotten</span> <span className="font-bold text-foreground">{data.rotten}</span></li>
                            <li className="flex justify-between items-center"><span className="text-yellow-600 font-medium">Sprouted</span> <span className="font-bold text-foreground">{data.sprout}</span></li>
                            <li className="flex justify-between items-center"><span className="text-orange-500 font-medium">Double Split</span> <span className="font-bold text-foreground">{data.double_split}</span></li>
                        </ul>
                    </div>
                    <div className="space-y-3">
                        <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">Size</h3>
                        <ul className="space-y-2 text-sm">
                            <li className="flex justify-between items-center"><span className="font-medium">Large {'>'} 70mm</span> <span className="font-bold text-foreground">{data.large}</span></li>
                            <li className="flex justify-between items-center"><span className="font-medium">Medium 40-70mm</span> <span className="font-bold text-foreground">{data.medium}</span></li>
                            <li className="flex justify-between items-center"><span className="font-medium">Small {'<'} 40mm</span> <span className="font-bold text-foreground">{data.small}</span></li>
                        </ul>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
